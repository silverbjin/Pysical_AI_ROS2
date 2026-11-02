"""Optional, bounded diagnostics. ROS and steady clocks are never subtracted.

Decoder imports and historical records work without ROS initialization. A boot
UUID identifies a clock domain, not equality with the analyst's current boot.
"""
import json
import os
from pathlib import Path
from threading import Lock, get_native_id
import time
from uuid import UUID, uuid4

MAX_BYTES, MAX_RECORDS = 4096, 20000
CLOCK_ID = 'linux/CLOCK_MONOTONIC'
KEYS = {
    'camera': ('submit_start', 'submit_end', 'acquire', 'scene_start', 'render_start', 'render_end',
               'readback_end', 'rgb_publish_start', 'rgb_publish_end', 'depth_publish_start',
               'depth_publish_end', 'info_publish_start', 'info_publish_end'),
    'detector': ('rgb_receive', 'slot_put', 'work_take', 'convert_start', 'convert_end',
                 'inference_start', 'inference_end', 'publish_start', 'publish_end'),
    'fusion': ('rgb_receive', 'depth_receive', 'detection_receive', 'bundle_select', 'work_take',
               'depth_start', 'depth_end', 'tf_start', 'tf_end', 'publish_start', 'publish_end'),
    'tracking': ('target_receive', 'decision', 'dispatch', 'gate_lost'),
}
FIELDS = {'schema_version', 'run_id', 'producer_id', 'pid', 'tid', 'clock_id', 'boot_id',
          'stage', 'event_sequence', 'source_frame', 'capture_ns', 'local_epoch',
          'native_sequence', 'times_ns', 'outcome', 'ros_now_ns'}


def _uuid(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError('canonical UUID required')
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError('canonical UUID required') from exc
    return value


def _integer(value, minimum=0, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not int or value < minimum or value > 2**64-1:
        raise ValueError('bounded nonnegative integer required')


def trace_options(enabled, run_id):
    """Validate launch/runner configuration before creating any engine or node."""
    if isinstance(enabled, str):
        if enabled.lower() not in ('true', 'false'):
            raise ValueError('trace_enabled must be an explicit boolean')
        enabled = enabled.lower() == 'true'
    elif type(enabled) is not bool:
        raise ValueError('trace_enabled must be an explicit boolean')
    if not isinstance(run_id, str):
        raise ValueError('trace_run_id must be a string')
    if enabled:
        _uuid(run_id)
    return dict(trace_enabled=enabled, trace_run_id=run_id)


def validate_record(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('trace schema1 fields required')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('trace schema1 required')
    for key in ('run_id', 'producer_id', 'boot_id'):
        _uuid(value[key])
    if (value['clock_id'] != CLOCK_ID or not isinstance(value['stage'], str)
            or value['stage'] not in KEYS):
        raise ValueError('known stage and Linux CLOCK_MONOTONIC required')
    for key in ('pid', 'tid', 'event_sequence'):
        _integer(value[key], 1)
    for key in ('capture_ns', 'local_epoch', 'native_sequence', 'ros_now_ns'):
        _integer(value[key], nullable=True)
    source, outcome = value['source_frame'], value['outcome']
    if (not isinstance(source, str) or not isinstance(outcome, str) or not outcome
            or (value['capture_ns'] is not None and not source)):
        raise ValueError('source frame and outcome required')
    source.encode('utf-8')
    outcome.encode('utf-8')
    stage, times = value['stage'], value['times_ns']
    if not isinstance(times, dict) or not times or not set(times) <= set(KEYS[stage]):
        raise ValueError('known nonempty stage times required')
    for ns in times.values():
        _integer(ns, 1)
    if stage == 'camera':
        _integer(value['native_sequence'], 1)
        _integer(value['local_epoch'])
    elif value['native_sequence'] is not None:
        raise ValueError('native sequence exists only at camera source')
    if value['capture_ns'] is None and stage != 'tracking':
        raise ValueError('capture required outside control diagnostics')
    if outcome == 'PUBLISHED' and stage != 'tracking' and set(times) != set(KEYS[stage]):
        raise ValueError('published summary requires every stage boundary')
    # Receive streams are independent; depth/TF can repeat for several boxes.
    # Check actual causal pairs, not a fabricated sort of independent inputs.
    if stage in ('camera', 'detector'):
        present = [times[k] for k in KEYS[stage] if k in times]
        if present != sorted(present):
            raise ValueError('negative stage duration')
    else:
        pairs = [('bundle_select', 'work_take'), ('work_take', 'depth_start'),
                 ('rgb_receive', 'bundle_select'), ('depth_receive', 'bundle_select'),
                 ('detection_receive', 'bundle_select'), ('depth_start', 'tf_start'),
                 ('depth_end', 'tf_end'), ('tf_end', 'publish_start'),
                 ('depth_end', 'publish_start'),
                 ('depth_start', 'depth_end'), ('tf_start', 'tf_end'),
                 ('publish_start', 'publish_end'), ('target_receive', 'decision'),
                 ('decision', 'dispatch'), ('decision', 'gate_lost')]
        for start, end in pairs:
            if start in times and end in times and times[start] > times[end]:
                raise ValueError('negative stage duration')
    return value


def decode_record(payload: str) -> dict:
    if not isinstance(payload, str) or len(payload.encode('utf-8')) > MAX_BYTES:
        raise ValueError('oversize trace payload')
    def object_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate JSON key')
            value[key] = item
        return value
    def invalid_constant(value):
        raise ValueError('nonfinite JSON constant: '+value)
    try:
        return validate_record(json.loads(payload, object_pairs_hook=object_pairs,
                                          parse_constant=invalid_constant))
    except (TypeError, KeyError, OverflowError) as exc:
        raise ValueError('invalid trace record') from exc


class TracePublisher:
    MAX_BYTES, MAX_RECORDS = MAX_BYTES, MAX_RECORDS

    def __init__(self, node, topic, *, enabled: bool, run_id: str):
        self.enabled, self.publisher, self.closed = bool(enabled), None, False
        self.lock = Lock()
        self._stats = dict(attempted=0, emitted=0, dropped=0, oversize=0, errors=0)
        if not self.enabled:
            return
        self.run_id = _uuid(run_id)
        if time.get_clock_info('monotonic').implementation != 'clock_gettime(CLOCK_MONOTONIC)':
            raise ValueError('trace requires explicit Linux CLOCK_MONOTONIC')
        self.boot_id = _uuid(Path('/proc/sys/kernel/random/boot_id').read_text().strip())
        self.producer_id, self.pid = str(uuid4()), os.getpid()
        self.logger, self.topic = node.get_logger(), topic
        # Lazy imports preserve offline decoder use without ROS installed.
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
        from std_msgs.msg import String
        self.message_type = String
        self.publisher = node.create_publisher(String, topic, QoSProfile(
            depth=32, history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE))
        node.context.on_shutdown(self.close)

    @property
    def stats(self):
        with self.lock:
            return self._stats.copy()

    def emit(self, stage, *, source_frame, capture_ns, local_epoch, times_ns, outcome,
             native_sequence=None, ros_now_ns=None) -> bool:
        if not self.enabled:
            return False
        with self.lock:
            self._stats['attempted'] += 1
            if self.closed or self._stats['attempted'] > self.MAX_RECORDS:
                self._stats['dropped'] += 1
                return False
            try:
                record = dict(schema_version=1, run_id=self.run_id, producer_id=self.producer_id,
                    pid=self.pid, tid=get_native_id(), clock_id=CLOCK_ID, boot_id=self.boot_id,
                    stage=stage, event_sequence=self._stats['attempted'],
                    source_frame=source_frame, capture_ns=capture_ns, local_epoch=local_epoch,
                    native_sequence=native_sequence, times_ns=dict(times_ns), outcome=outcome,
                    ros_now_ns=ros_now_ns)
                validate_record(record)
                payload = json.dumps(record, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
                if len(payload.encode('utf-8')) > self.MAX_BYTES:
                    self._stats['oversize'] += 1
                    self._stats['dropped'] += 1
                    return False
                self.publisher.publish(self.message_type(data=payload))
                self._stats['emitted'] += 1
                return True
            except Exception:
                self._stats['errors'] += 1
                self._stats['dropped'] += 1
                return False

    def close(self):
        if not self.enabled:
            return
        with self.lock:
            if self.closed:
                return
            self.closed = True
            summary = dict(run_id=self.run_id, producer_id=self.producer_id, topic=self.topic,
                           **self._stats)
        try:
            self.logger.info('trace_totals '+json.dumps(summary, sort_keys=True))
        except Exception:
            pass  # missing summary is unknown, never inferred as zero drops
