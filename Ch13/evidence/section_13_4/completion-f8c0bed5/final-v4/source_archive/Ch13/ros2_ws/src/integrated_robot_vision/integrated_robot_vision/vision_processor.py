"""Capture-time TF fusion. Never substitute a latest transform on failure."""
from copy import deepcopy
from collections import OrderedDict
import json
from threading import Event, RLock, Thread
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped
from integrated_robot_interfaces.msg import TrackedTarget
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from tf2_geometry_msgs import do_transform_point
from tf2_ros import Buffer, TransformException, TransformListener
from vision_msgs.msg import Detection2DArray

from .cache import RGBDCache, seconds, nanoseconds
from .contracts import Box2D, Observation, vector
from .freshness import ClockGate, LatestSlot
from .geometry import decode_depth, deproject, sample_depth, validate_depth_range
from .tracker import TrackManager
from .trace import TracePublisher


def lookup_capture_point(buffer, point: np.ndarray, source_frame: str, stamp_msg,
                         target_frame: str = 'odom') -> PointStamped:
    if seconds(stamp_msg) <= 0 or not source_frame or not target_frame:
        raise ValueError('explicit positive capture time and named frames required')
    point = vector(point, (3,))
    msg = PointStamped()
    msg.header.frame_id, msg.header.stamp = source_frame, deepcopy(stamp_msg)
    msg.point.x, msg.point.y, msg.point.z = point.tolist()
    transform = buffer.lookup_transform(target_frame, source_frame, Time.from_msg(stamp_msg),
                                        timeout=Duration(seconds=.1))
    result = do_transform_point(msg, transform)
    result.header.stamp = deepcopy(stamp_msg)
    return result


def capture_observations(bundle, boxes, buffer, *, still_valid, depth_range=(.1, 5.), trace_times=None):
    if not still_valid():
        return []
    image = bundle.depth
    if trace_times is not None:
        trace_times['depth_start'] = time.monotonic_ns()
    depth = decode_depth(bytes(image.data), image.encoding, image.width, image.height,
                         image.step, bool(image.is_bigendian))
    if trace_times is not None:
        trace_times['depth_end'] = time.monotonic_ns()
    observations = []
    for box in boxes:
        if box.score < .5 or not still_valid():
            continue
        bounds = dict(min_depth_m=depth_range[0], max_depth_m=depth_range[1])
        d, mad = sample_depth(depth, box, **bounds)
        point = deproject(box.cx, box.cy, d, bundle.intrinsics, **bounds)
        if trace_times is not None:
            trace_times['depth_end'] = time.monotonic_ns()
            trace_times.setdefault('tf_start', time.monotonic_ns())
        transformed = lookup_capture_point(buffer, point, bundle.intrinsics.frame_id,
                                            bundle.rgb.header.stamp)
        if trace_times is not None:
            trace_times['tf_end'] = time.monotonic_ns()
        if not still_valid():
            return []
        # Isotropic depth-sample heuristic is rotation invariant, not a
        # statistically calibrated object-position uncertainty estimate.
        covariance = np.eye(3) * max(1e-6, (1.4826 * mad) ** 2)
        observations.append(Observation(bundle.stamp, bundle.epoch,
                                        bundle.intrinsics.calibration_id, 'odom', box,
                                        [transformed.point.x, transformed.point.y, transformed.point.z],
                                        covariance))
    return observations


class VisionProcessor(Node):
    """Small callbacks and one worker; control nodes run in other processes."""

    def __init__(self):
        super().__init__('vision_processor')
        self.depth_range = (self.declare_parameter('min_depth_m', .1).value,
                            self.declare_parameter('max_depth_m', 5.).value)
        validate_depth_range(*self.depth_range)
        filter_mode = self.declare_parameter('filter_mode', 'time_constant').value
        tau = self.declare_parameter('filter_tau_s', .2).value
        alpha = self.declare_parameter('filter_alpha', .25).value
        if filter_mode not in ('time_constant', 'fixed_alpha') or not 0 < alpha <= 1:
            raise ValueError('known filter mode and alpha in (0,1] required')
        self.lock, self.stopping = RLock(), Event()
        self.gate, self.cache, self.slot = ClockGate(), RGBDCache(), LatestSlot()
        self.trace = TracePublisher(self, '/vision/fusion_trace',
            enabled=self.declare_parameter('trace_enabled', False).value,
            run_id=self.declare_parameter('trace_run_id', '').value)
        self.trace_receipts = {kind: OrderedDict() for kind in ('rgb', 'depth', 'detection')}
        self.tracker = TrackManager(tau=tau, alpha=alpha if filter_mode == 'fixed_alpha' else None)
        self.last_source_header, self.last_published_state = None, None
        self.last_epoch, self.last_stamp = -1, 0.
        self.last_submitted_ns = 0
        self.pending_detections = {}
        self.candidate_events = 0
        self.tf_buffer = Buffer(node=self)
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.raw_pub = self.create_publisher(PointStamped, '/vision/target_raw', 10)
        self.filtered_pub = self.create_publisher(PointStamped, '/vision/target_filtered', 10)
        self.tracked_pub = self.create_publisher(TrackedTarget, '/vision/tracked_target', 10)
        self.status_pub = self.create_publisher(String, '/vision/status', 10)
        # A complete capture needs all streams. Best-effort independent image
        # loss is not equivalent to intentionally selecting the newest bundle.
        # Keep transport bounded; ClockGate still rejects anything over300ms.
        capture_qos = QoSProfile(depth=5)
        self.subscriptions_owned = [
            self.create_subscription(Image, '/camera/color/image_raw', self.on_rgb, capture_qos),
            self.create_subscription(Image, '/camera/aligned_depth_to_color/image_raw', self.on_depth, capture_qos),
            self.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info, capture_qos),
            self.create_subscription(Detection2DArray, '/vision/detections', self.on_detections, capture_qos),
        ]
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.watchdog = self.create_timer(.05, self.poll, clock=self.steady_clock)
        self.worker = Thread(target=self.work, name='rgbd-fusion', daemon=False)
        self.worker.start()

    def report(self, reason, **details):
        with self.lock:
            if self.stopping.is_set():
                return
            msg = String()
            msg.data = json.dumps({'status': reason, 'epoch': self.gate.epoch, **details})
            self.status_pub.publish(msg)
            status = {'RESET': 'RESET', 'TF_UNAVAILABLE': 'TF_UNAVAILABLE',
                      'INVALID_CALIBRATION': 'INVALID', 'INVALID_RGB': 'INVALID',
                      'INVALID_DEPTH': 'INVALID', 'INVALID_DETECTION': 'INVALID',
                      'INVALID_DEPTH_OR_GEOMETRY': 'INVALID', 'NO_FRESH_ALIGNED_PAIR': 'INVALID',
                      'EMPTY_OR_EXPIRED': 'LOST', 'WORKER_ERROR': 'INVALID'}.get(reason)
            if status is not None:
                if reason in ('RESET', 'INVALID_CALIBRATION', 'WORKER_ERROR'):
                    self.tracker.reset(status, self.gate.epoch)
                    estimate = self.tracker.estimate
                else:
                    estimate = self.tracker.invalidate(status)
                self.publish_track(estimate)

    def candidate_event(self, header, event, **details):
        """Bounded ingress/selection evidence, including jobs never submitted.

        Diagnostic only: it cannot renew a receipt, target or control lease.
        The existing status observer preserves these records with the trial UUID.
        """
        if not self.trace.enabled or self.candidate_events >= 20000:
            return
        self.candidate_events += 1
        self.report('CANDIDATE', run_id=self.trace.run_id,
                    sequence=self.candidate_events, event=event,
                    capture_ns=nanoseconds(header.stamp), source_frame=header.frame_id,
                    monotonic_ns=time.monotonic_ns(),
                    ros_now_ns=self.get_clock().now().nanoseconds, **details)

    def observe_clock(self):
        with self.lock:
            ros_now, wall_now = self.get_clock().now().nanoseconds / 1e9, time.monotonic()
            epoch = self.gate.observe(ros_now, wall_now)
            if epoch != self.last_epoch:
                if self.last_epoch >= 0:
                    # tf2's default backward-jump threshold is one second;
                    # our smaller epoch resets must discard dynamic history too.
                    self.tf_buffer.clear()
                self.cache.clear(epoch)
                self.pending_detections.clear()
                for receipts in self.trace_receipts.values():
                    receipts.clear()
                self.slot.take(0)
                self.last_stamp, self.last_epoch = 0., epoch
                self.last_submitted_ns = 0
                self.report('RESET')
            expired = self.tracker.expire(ros_now, wall_now)
            if expired is not None:
                self.publish_track(expired)
            return ros_now, wall_now, epoch

    def poll(self):
        with self.lock:
            self.try_pending(*self.observe_clock())

    def on_info(self, msg):
        with self.lock:
            now, wall, epoch = self.observe_clock()
            previous = self.cache.calibration_id
            try:
                self.cache.add_info(msg, epoch)
                self.candidate_event(msg.header, 'INFO_RECEIVED')
            except ValueError:
                self.report('INVALID_CALIBRATION')
            if previous != self.cache.calibration_id:
                self.slot.take(0)
                self.pending_detections.clear()
                self.report('RESET')
            self.try_pending(now, wall, epoch)

    def on_rgb(self, msg):
        received_ns = time.monotonic_ns() if self.trace.enabled else None
        with self.lock:
            now, wall, epoch = self.observe_clock()
            try:
                self.cache.add_rgb(msg, epoch)
                self.remember_trace('rgb', msg.header.stamp, received_ns)
                self.candidate_event(msg.header, 'RGB_RECEIVED')
            except ValueError:
                self.report('INVALID_RGB')
            self.try_pending(now, wall, epoch)

    def on_depth(self, msg):
        received_ns = time.monotonic_ns() if self.trace.enabled else None
        with self.lock:
            now, wall, epoch = self.observe_clock()
            try:
                self.cache.add_depth(msg, epoch)
                self.remember_trace('depth', msg.header.stamp, received_ns)
                self.candidate_event(msg.header, 'DEPTH_RECEIVED')
            except ValueError:
                self.report('INVALID_DEPTH')
            self.try_pending(now, wall, epoch)

    def current(self, bundle):
        with self.lock:
            now, wall, _ = self.observe_clock()
            return (not self.stopping.is_set() and self.cache.current(bundle)
                    and bundle.stamp > self.last_stamp
                    and self.gate.valid(bundle.stamp, bundle.epoch, now, wall, bundle.receipt_wall))

    def on_detections(self, msg):
        received_ns = time.monotonic_ns() if self.trace.enabled else None
        with self.lock:
            now, wall, epoch = self.observe_clock()
            boxes = []
            try:
                if nanoseconds(msg.header.stamp) <= 0 or msg.header.frame_id != 'camera_optical_frame':
                    raise ValueError('positive capture time and canonical optical frame required')
                stamp = seconds(msg.header.stamp)
                key = nanoseconds(msg.header.stamp)
                self.candidate_event(msg.header, 'DETECTION_RECEIVED')
                if stamp <= self.last_stamp or key <= self.last_submitted_ns or key in self.pending_detections:
                    self.candidate_event(msg.header, 'OLD_OR_DUPLICATE')
                    return  # old/duplicate inference never invalidates or renews a newer track
                for detection in msg.detections[:32]:
                    if not detection.results:
                        continue
                    best = max(detection.results, key=lambda v: v.hypothesis.score).hypothesis
                    if best.score >= .5:
                        box = detection.bbox
                        boxes.append(Box2D(box.center.position.x, box.center.position.y,
                                           box.size_x, box.size_y, best.class_id, best.score))
                self.remember_trace('detection', msg.header.stamp, received_ns)
                self.pending_detections[key] = (deepcopy(msg.header), boxes, epoch, wall)
                while len(self.pending_detections) > 10:  # same bound as the RGB-D cache
                    removed = self.pending_detections.pop(min(self.pending_detections))
                    self.candidate_event(removed[0], 'CAPACITY_EVICTED')
                self.try_pending(now, wall, epoch)
            except (ValueError, RuntimeError, TypeError):
                self.report('INVALID_DETECTION')

    @property
    def pending_detection(self):
        with self.lock:
            return (self.pending_detections[max(self.pending_detections)]
                    if self.pending_detections else None)

    def remember_trace(self, kind, stamp, received_ns):
        # Scalar metadata only, same ten-capture bound as the existing cache.
        if received_ns is None:
            return
        receipts = self.trace_receipts[kind]
        key = nanoseconds(stamp)
        receipts[key] = received_ns
        receipts.move_to_end(key)
        while len(receipts) > 10:
            receipts.popitem(last=False)

    def try_pending(self, now, wall, epoch):
        """Newest COMPLETE capture wins; an unpaired newer one cannot erase it.

        Candidate metadata shares the 10-image cache bound. The processing
        slot is still capacity one; no capture or receipt deadline is renewed.
        """
        expired = False
        for key, pending in sorted(list(self.pending_detections.items()), reverse=True):
            header, boxes, source_epoch, received = pending
            if (seconds(header.stamp) <= self.last_stamp or
                    not self.gate.valid(seconds(header.stamp), source_epoch, now, wall, received)):
                self.pending_detections.pop(key, None)
                self.candidate_event(header, 'EXPIRED_OR_OLD',
                                     ros_age_s=now-seconds(header.stamp),
                                     receipt_age_s=wall-received)
                expired = True
                continue
            bundle = self.cache.match(header.stamp, header.frame_id, epoch)
            if bundle is None:
                reason = ('WAIT_RGB' if seconds(header.stamp) not in self.cache.rgb else
                          'WAIT_DEPTH' if not self.cache.depth else
                          'WAIT_INFO' if not self.cache.info else 'WAIT_ALIGNED_PAIR')
                self.candidate_event(header, reason,
                    depth_captures=[nanoseconds(v[0].header.stamp) for v in self.cache.depth.values()],
                    rgb_captures=[nanoseconds(v[0].header.stamp) for v in self.cache.rgb.values()])
                continue
            if self.current(bundle):
                for previous in list(self.pending_detections):
                    if previous <= key:
                        if previous != key:
                            self.candidate_event(self.pending_detections[previous][0], 'SUPERSEDED')
                        del self.pending_detections[previous]
                trace_times = None
                if self.trace.enabled:
                    trace_times = dict(bundle_select=time.monotonic_ns())
                    for kind, source_stamp in [('rgb', bundle.rgb.header.stamp),
                                              ('depth', bundle.depth.header.stamp),
                                              ('detection', header.stamp)]:
                        received = self.trace_receipts[kind].get(nanoseconds(source_stamp))
                        if received is not None:
                            trace_times[kind+'_receive'] = received
                with self.slot.condition:
                    if self.slot.item is not None:
                        self.candidate_event(self.slot.item[0].rgb.header, 'SLOT_OVERWRITTEN')
                    self.slot.replace((bundle, boxes, trace_times))
                self.candidate_event(header, 'SUBMITTED')
                self.last_submitted_ns = key
                return
            self.candidate_event(header, 'BUNDLE_NOT_CURRENT',
                                 ros_age_s=now-bundle.stamp,
                                 receipt_age_s=wall-bundle.receipt_wall)
        if expired and not self.pending_detections:
            self.report('NO_FRESH_ALIGNED_PAIR')

    def work(self):
        while not self.stopping.is_set():
            item = self.slot.take(.1)
            if item is None:
                continue
            bundle, boxes, trace_times = item
            with self.lock:
                self.candidate_event(bundle.rgb.header, 'WORKER_TAKE')
            if trace_times is not None:
                trace_times['work_take'] = time.monotonic_ns()
            outcome, ros_now_ns = 'WORKER_ERROR', None
            try:
                observations = capture_observations(bundle, boxes, self.tf_buffer,
                                                     still_valid=lambda: self.current(bundle),
                                                     depth_range=self.depth_range,
                                                     trace_times=trace_times)
                with self.lock:
                    if self.current(bundle):
                        self.publish_observations(observations, bundle, trace_times=trace_times)
                        outcome = ('PUBLISHED' if trace_times is not None and
                                   'publish_end' in trace_times and self.tracker.estimate is not None
                                   and self.tracker.estimate.valid else 'NO_TARGET')
                        if trace_times is not None:
                            ros_now_ns = self.get_clock().now().nanoseconds
                        self.last_stamp = bundle.stamp
                    elif not self.stopping.is_set():
                        outcome = 'EMPTY_OR_EXPIRED'
                        self.report('EMPTY_OR_EXPIRED')
            except TransformException as exc:
                outcome = 'TF_UNAVAILABLE'
                self.report('TF_UNAVAILABLE', detail=str(exc),
                            capture_ns=nanoseconds(bundle.rgb.header.stamp),
                            source_frame=bundle.intrinsics.frame_id, target_frame='odom',
                            ros_age_s=self.get_clock().now().nanoseconds/1e9-bundle.stamp)
            except ValueError:
                outcome = 'INVALID_DEPTH_OR_GEOMETRY'
                self.report('INVALID_DEPTH_OR_GEOMETRY')
            except Exception as exc:
                self.get_logger().error(f'fusion worker failed: {exc!r}')
                self.report('WORKER_ERROR')
            finally:
                with self.lock:
                    self.candidate_event(bundle.rgb.header, 'WORKER_DONE', outcome=outcome)
                if trace_times is not None:
                    self.trace.emit('fusion', source_frame=bundle.rgb.header.frame_id,
                        capture_ns=nanoseconds(bundle.rgb.header.stamp), local_epoch=bundle.epoch,
                        times_ns=trace_times, outcome=outcome,
                        ros_now_ns=ros_now_ns if ros_now_ns is not None else self.get_clock().now().nanoseconds)

    def publish_observations(self, observations, bundle, *, trace_times=None):
        now, wall, _ = self.observe_clock()
        estimate = self.tracker.update(observations, now, wall)
        self.publish_track(estimate, bundle.rgb.header if estimate is not None and estimate.valid else None,
                           trace_times=trace_times)
        self.report('TRACKED' if estimate is not None and estimate.valid else 'TARGET_INVALID')

    def publish_track(self, estimate, source_header=None, *, trace_times=None):
        if estimate is None or self.stopping.is_set():
            return
        key = (estimate.track_id, estimate.stamp, estimate.valid, estimate.status)
        if key == self.last_published_state:
            return
        if source_header is not None:
            self.last_source_header = deepcopy(source_header)
        if self.last_source_header is None:
            return
        source = self.last_source_header
        tracked = TrackedTarget()
        tracked.header.frame_id, tracked.header.stamp = 'odom', deepcopy(source.stamp)
        tracked.source_header = deepcopy(source)
        tracked.processed_at = self.get_clock().now().to_msg()
        tracked.track_id, tracked.class_id, tracked.score = estimate.track_id, estimate.class_id, float(self.tracker.score)
        tracked.position.x, tracked.position.y, tracked.position.z = estimate.point.tolist()
        tracked.covariance = estimate.covariance.reshape(-1).tolist()
        tracked.valid, tracked.status = estimate.valid, estimate.status
        if estimate.valid:
            # Only the selected target is published, not every competing box.
            obs = self.tracker.observation
            msg = PointStamped()
            msg.header = deepcopy(tracked.header)
            msg.point.x, msg.point.y, msg.point.z = obs.point.tolist()
            self.raw_pub.publish(msg)
            filtered = PointStamped()
            filtered.header, filtered.point = deepcopy(tracked.header), deepcopy(tracked.position)
            self.filtered_pub.publish(filtered)
        if trace_times is not None:
            trace_times['publish_start'] = time.monotonic_ns()
        self.tracked_pub.publish(tracked)
        if trace_times is not None:
            trace_times['publish_end'] = time.monotonic_ns()
        self.last_published_state = key

    def destroy_node(self):
        with self.lock:
            self.stopping.set()
            self.slot.close()
        self.worker.join(timeout=2)
        if self.worker.is_alive():
            raise RuntimeError('fusion worker failed to stop before ROS destruction')
        self.trace.close()
        return super().destroy_node()


def make_executor():
    # ROS callbacks only validate/cache; TF waits and depth work run on worker.
    # The executor can keep accepting TF while that worker is blocked.
    return SingleThreadedExecutor()


def main(args=None):
    from .execution import run_node
    run_node(VisionProcessor, args=args, executor_factory=make_executor)
