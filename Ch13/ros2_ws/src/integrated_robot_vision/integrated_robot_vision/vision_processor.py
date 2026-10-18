"""Capture-time TF fusion. Never substitute a latest transform on failure."""
from copy import deepcopy
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
from rclpy.qos import qos_profile_sensor_data
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


def capture_observations(bundle, boxes, buffer, *, still_valid, depth_range=(.1, 5.)):
    if not still_valid():
        return []
    image = bundle.depth
    depth = decode_depth(bytes(image.data), image.encoding, image.width, image.height,
                         image.step, bool(image.is_bigendian))
    observations = []
    for box in boxes:
        if box.score < .5 or not still_valid():
            continue
        bounds = dict(min_depth_m=depth_range[0], max_depth_m=depth_range[1])
        d, mad = sample_depth(depth, box, **bounds)
        point = deproject(box.cx, box.cy, d, bundle.intrinsics, **bounds)
        transformed = lookup_capture_point(buffer, point, bundle.intrinsics.frame_id,
                                            bundle.rgb.header.stamp)
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
        self.tracker = TrackManager(tau=tau, alpha=alpha if filter_mode == 'fixed_alpha' else None)
        self.last_source_header, self.last_published_state = None, None
        self.last_epoch, self.last_stamp = -1, 0.
        self.pending_detection = None
        self.tf_buffer = Buffer(node=self)
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.raw_pub = self.create_publisher(PointStamped, '/vision/target_raw', 10)
        self.filtered_pub = self.create_publisher(PointStamped, '/vision/target_filtered', 10)
        self.tracked_pub = self.create_publisher(TrackedTarget, '/vision/tracked_target', 10)
        self.status_pub = self.create_publisher(String, '/vision/status', 10)
        self.subscriptions_owned = [
            self.create_subscription(Image, '/camera/color/image_raw', self.on_rgb, qos_profile_sensor_data),
            self.create_subscription(Image, '/camera/aligned_depth_to_color/image_raw', self.on_depth, qos_profile_sensor_data),
            self.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info, qos_profile_sensor_data),
            self.create_subscription(Detection2DArray, '/vision/detections', self.on_detections, qos_profile_sensor_data),
        ]
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.watchdog = self.create_timer(.05, self.poll, clock=self.steady_clock)
        self.worker = Thread(target=self.work, name='rgbd-fusion', daemon=False)
        self.worker.start()

    def report(self, reason):
        with self.lock:
            if self.stopping.is_set():
                return
            msg = String()
            msg.data = json.dumps({'status': reason, 'epoch': self.gate.epoch})
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
                self.pending_detection = None
                self.slot.take(0)
                self.last_stamp, self.last_epoch = 0., epoch
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
            except ValueError:
                self.report('INVALID_CALIBRATION')
            if previous != self.cache.calibration_id:
                self.slot.take(0)
                self.pending_detection = None
                self.report('RESET')
            self.try_pending(now, wall, epoch)

    def on_rgb(self, msg):
        with self.lock:
            now, wall, epoch = self.observe_clock()
            try:
                self.cache.add_rgb(msg, epoch)
            except ValueError:
                self.report('INVALID_RGB')
            self.try_pending(now, wall, epoch)

    def on_depth(self, msg):
        with self.lock:
            now, wall, epoch = self.observe_clock()
            try:
                self.cache.add_depth(msg, epoch)
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
        with self.lock:
            now, wall, epoch = self.observe_clock()
            boxes = []
            try:
                if nanoseconds(msg.header.stamp) <= 0 or msg.header.frame_id != 'camera_optical_frame':
                    raise ValueError('positive capture time and canonical optical frame required')
                stamp = seconds(msg.header.stamp)
                if stamp <= self.last_stamp or (self.pending_detection is not None
                        and stamp <= seconds(self.pending_detection[0].stamp)):
                    return  # old/duplicate inference never invalidates or renews a newer track
                for detection in msg.detections[:32]:
                    if not detection.results:
                        continue
                    best = max(detection.results, key=lambda v: v.hypothesis.score).hypothesis
                    if best.score >= .5:
                        box = detection.bbox
                        boxes.append(Box2D(box.center.position.x, box.center.position.y,
                                           box.size_x, box.size_y, best.class_id, best.score))
                self.pending_detection = (deepcopy(msg.header), boxes, epoch, wall)
                self.slot.take(0)  # only the newest waiting detection/frame is useful
                self.try_pending(now, wall, epoch)
            except (ValueError, RuntimeError, TypeError):
                self.report('INVALID_DETECTION')

    def try_pending(self, now, wall, epoch):
        """Wait for cross-topic arrival, never extend capture/receipt deadlines."""
        pending = self.pending_detection
        if pending is None:
            return
        header, boxes, source_epoch, received = pending
        if not self.gate.valid(seconds(header.stamp), source_epoch, now, wall, received):
            self.pending_detection = None
            self.report('NO_FRESH_ALIGNED_PAIR')
            return
        bundle = self.cache.match(header.stamp, header.frame_id, epoch)
        if bundle is None:
            return  # watchdog and subsequent RGB/depth callbacks retry within original TTL
        self.pending_detection = None
        if self.current(bundle):
            self.slot.replace((bundle, boxes))
        else:
            self.report('NO_FRESH_ALIGNED_PAIR')

    def work(self):
        while not self.stopping.is_set():
            item = self.slot.take(.1)
            if item is None:
                continue
            bundle, boxes = item
            try:
                observations = capture_observations(bundle, boxes, self.tf_buffer,
                                                     still_valid=lambda: self.current(bundle),
                                                     depth_range=self.depth_range)
                with self.lock:
                    if self.current(bundle):
                        self.publish_observations(observations, bundle)
                        self.last_stamp = bundle.stamp
                    elif not self.stopping.is_set():
                        self.report('EMPTY_OR_EXPIRED')
            except TransformException:
                self.report('TF_UNAVAILABLE')
            except ValueError:
                self.report('INVALID_DEPTH_OR_GEOMETRY')
            except Exception as exc:
                self.get_logger().error(f'fusion worker failed: {exc!r}')
                self.report('WORKER_ERROR')

    def publish_observations(self, observations, bundle):
        now, wall, _ = self.observe_clock()
        estimate = self.tracker.update(observations, now, wall)
        self.publish_track(estimate, bundle.rgb.header if estimate is not None and estimate.valid else None)
        self.report('TRACKED' if estimate is not None and estimate.valid else 'TARGET_INVALID')

    def publish_track(self, estimate, source_header=None):
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
        self.tracked_pub.publish(tracked)
        self.last_published_state = key

    def destroy_node(self):
        with self.lock:
            self.stopping.set()
            self.slot.close()
        self.worker.join(timeout=2)
        if self.worker.is_alive():
            raise RuntimeError('fusion worker failed to stop before ROS destruction')
        return super().destroy_node()


def make_executor():
    # ROS callbacks only validate/cache; TF waits and depth work run on worker.
    # The executor can keep accepting TF while that worker is blocked.
    return SingleThreadedExecutor()


def main(args=None):
    from .execution import run_node
    run_node(VisionProcessor, args=args, executor_factory=make_executor)
