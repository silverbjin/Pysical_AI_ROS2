"""Wire schema is offline; diagnostics cannot become a validity or control input."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from integrated_robot_vision.trace import TracePublisher, decode_record, validate_record

RUN = '424240ff-0bfe-4a4b-92d4-93f6a78d49b8'
BOOT = '11111111-1111-4111-8111-111111111111'


def record():
    return dict(schema_version=1, run_id=RUN, producer_id=BOOT, pid=1, tid=2,
                clock_id='linux/CLOCK_MONOTONIC', boot_id=BOOT, stage='tracking',
                event_sequence=1, source_frame='camera_optical_frame', capture_ns=1_000_000_000,
                local_epoch=None, native_sequence=None, times_ns={'decision': 10},
                outcome='NO_COMMAND', ros_now_ns=1_100_000_000)


def test_offline_schema_retains_original_domains_and_supports_missing_target():
    value = record()
    assert decode_record(json.dumps(value)) == value == validate_record(value)
    value.update(capture_ns=None, source_frame='', ros_now_ns=0)
    assert validate_record(value)['capture_ns'] is None


@pytest.mark.parametrize('key,bad', [
    ('schema_version', 2), ('schema_version', True), ('pid', -1), ('tid', 0),
    ('run_id', ''), ('producer_id', 'not-uuid'), ('boot_id', ''),
    ('clock_id', 'time.time'), ('stage', 'unknown'), ('capture_ns', -1),
    ('capture_ns', 1.), ('capture_ns', True), ('ros_now_ns', -1),
    ('event_sequence', 0), ('local_epoch', -1), ('native_sequence', -1),
    ('times_ns', {'decision': -10}), ('times_ns', {'unknown': 10}),
    ('times_ns', {'decision': 11, 'dispatch': 10}), ('times_ns', {}),
])
def test_invalid_schema_never_yields_latency(key, bad):
    value = record()
    value[key] = bad
    with pytest.raises(ValueError):
        validate_record(value)


def test_decoder_rejects_duplicate_keys_nan_and_oversize_bytes():
    for payload in ('{"schema_version":1,"schema_version":1}', '{"capture_ns":NaN}',
                    '한'*2000):
        with pytest.raises(ValueError):
            decode_record(payload)


class Node:
    """Only transport fault/byte-limit tests use this peer; ROS tests use actual nodes."""
    def __init__(self):
        self.messages = []
        self.publisher = SimpleNamespace(publish=self.messages.append)
        self.context = SimpleNamespace(on_shutdown=lambda callback: None)
    def create_publisher(self, *args, **kwargs):
        return self.publisher
    def get_logger(self):
        return SimpleNamespace(info=lambda text: None)


def fields():
    value = record()
    return {key: value[key] for key in ('source_frame', 'capture_ns', 'local_epoch',
                                      'times_ns', 'outcome', 'ros_now_ns')}


def test_disabled_zero_emission_and_enabled_uuid_rejection():
    node = Node()
    disabled = TracePublisher(node, '/trace', enabled=False, run_id='')
    assert not disabled.emit('tracking', **fields()) and node.messages == []
    assert disabled.stats['attempted'] == 0 and disabled.publisher is None
    with pytest.raises(ValueError):
        TracePublisher(node, '/trace', enabled=True, run_id='invalid')


def test_occurrence_ten_is_not_replaced_by_emit_time_one_hundred():
    node = Node()
    trace = TracePublisher(node, '/trace', enabled=True, run_id=RUN)
    with patch('time.monotonic_ns', return_value=100):
        assert trace.emit('tracking', **fields())
    decoded = decode_record(node.messages[0].data)
    assert decoded['times_ns']['decision'] == 10
    assert decoded['ros_now_ns'] == 1_100_000_000
    assert trace.MAX_BYTES == 4096 and trace.MAX_RECORDS == 20000


def test_utf8_bytes_limit_and_transport_failure_are_local():
    node = Node()
    trace = TracePublisher(node, '/trace', enabled=True, run_id=RUN)
    args = fields()
    args['source_frame'] = '한'*1400
    assert not trace.emit('tracking', **args)
    assert trace.stats['oversize'] == trace.stats['dropped'] == 1
    assert trace.emit('tracking', **fields())
    assert len(node.messages[0].data.encode('utf-8')) <= 4096
    def fail(_):
        raise RuntimeError('transport failure')
    node.publisher.publish = fail
    assert not trace.emit('tracking', **fields())
    assert trace.stats['errors'] == 1 and trace.stats['dropped'] == 2


def test_twenty_thousand_attempt_limit_is_bounded_without_subscribers():
    node = Node()
    node.publisher.publish = lambda message: None
    trace = TracePublisher(node, '/trace', enabled=True, run_id=RUN)
    for _ in range(20000):
        assert trace.emit('tracking', **fields())
    assert not trace.emit('tracking', **fields())
    assert trace.stats['emitted'] == 20000 and trace.stats['dropped'] == 1


def test_incompatible_python_clock_or_invalid_boot_refuses_enabled_trace(monkeypatch):
    import integrated_robot_vision.trace as module
    with monkeypatch.context() as m:
        m.setattr(module.time, 'get_clock_info', lambda _: SimpleNamespace(implementation='other'))
        with pytest.raises(ValueError):
            TracePublisher(Node(), '/trace', enabled=True, run_id=RUN)
    with patch.object(module.Path, 'read_text', return_value='not-uuid'):
        with pytest.raises(ValueError):
            TracePublisher(Node(), '/trace', enabled=True, run_id=RUN)
