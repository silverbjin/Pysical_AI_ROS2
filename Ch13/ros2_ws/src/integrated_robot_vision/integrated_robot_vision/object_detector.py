"""One inference worker, one newest waiting frame, original capture headers."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from threading import Event, RLock, Thread
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from std_srvs.srv import SetBool
from vision_msgs.msg import Detection2DArray

from .cache import RGBDCache, seconds
from .detectors import ColorFixtureBackend, YoloBackend, to_detection_array
from .freshness import ClockGate, LatestSlot
from .trace import TracePublisher


@dataclass(frozen=True)
class DetectionJob:
    image: object
    stamp: float
    epoch: int
    calibration_id: str
    info_stamp: float
    receipt_wall: float
    receipt_ros: float
    trace_times: object = None


class ObjectDetector(Node):
    def __init__(self, *, parameter_overrides=None):
        super().__init__('object_detector', parameter_overrides=parameter_overrides)
        self.backend_name = self.declare_parameter('backend', 'yolo').value
        weights = self.declare_parameter('weights_path', '').value
        expected_sha = self.declare_parameter('weights_sha256', '').value
        self.rate = self.declare_parameter('max_rate_hz', 10.).value
        self.delay = self.declare_parameter('processing_delay_s', 0.).value
        self.confidence = self.declare_parameter('confidence', .5).value
        if (not all(math.isfinite(v) for v in (self.rate, self.delay, self.confidence))
                or not 0 < self.rate <= 15 or self.delay < 0 or not .5 <= self.confidence <= 1):
            raise ValueError('rate in (0,15], nonnegative delay, confidence in [.5,1] required')
        if self.backend_name == 'yolo':
            if not weights or not Path(weights).is_absolute():
                raise FileNotFoundError('YOLO requires an explicit absolute local weights_path')
            self.backend = YoloBackend(Path(weights), expected_sha256=expected_sha or None)
        elif self.backend_name == 'color_fixture':
            self.backend = ColorFixtureBackend()
        else:
            raise ValueError('backend must be yolo or color_fixture; no fallback')
        # This executable owns one inference worker. Tiny320x240 connected
        # components must not recruit the default eight-way OpenCV pool while
        # the engine renders and control/TF processes compete for the same CPUs.
        # Configure after optional Ultralytics initialization, before any jobs.
        cv2.setNumThreads(1)
        self.bridge = CvBridge()
        self.lock, self.stopping = RLock(), Event()
        self.gate, self.cache, self.slot = ClockGate(), RGBDCache(), LatestSlot()
        self.trace = TracePublisher(self, '/vision/detector_trace',
            enabled=self.declare_parameter('trace_enabled', False).value,
            run_id=self.declare_parameter('trace_run_id', '').value)
        self.last_epoch, self.last_stamp = -1, 0.
        self.input_enabled = True
        self.input_events = 0
        self.input_service = self.create_service(SetBool, '~/set_input_enabled', self.set_input_enabled)
        self.pub = self.create_publisher(Detection2DArray, '/vision/detections', 5)
        self.status_pub = self.create_publisher(String, '/vision/detector_status', 10)
        self.rgb_sub = self.create_subscription(Image, '/camera/color/image_raw', self.on_rgb,
                                                 5)
        self.info_sub = self.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info,
                                                  5)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.watchdog = self.create_timer(.05, self.observe_clock, clock=self.steady_clock)
        self.worker = Thread(target=self.work, name='detector-inference', daemon=False)
        self.get_logger().info(f'explicit detector backend={self.backend_name}, max_rate_hz={self.rate}')
        self.worker.start()  # last constructor operation; no fallible setup after start

    def report(self, status, *, job=None, **details):
        if not self.stopping.is_set():
            msg = String()
            if job is not None:
                now, wall, _ = self.observe_clock()
                details.update(capture_ns=job.image.header.stamp.sec*1_000_000_000 +
                               job.image.header.stamp.nanosec,
                               receipt_ros_age_s=job.receipt_ros-job.stamp,
                               ros_age_s=now-job.stamp, wall_age_s=wall-job.receipt_wall,
                               artificial_delay_s=self.delay)
            msg.data = json.dumps({'backend': self.backend_name, 'status': status,
                                   'epoch': self.gate.epoch, **details})
            self.status_pub.publish(msg)

    def set_input_enabled(self, request, response):
        """Pause consumer ingress, not native camera power or arm ownership."""
        with self.lock:
            self.input_enabled = bool(request.data)
            self.cache.clear(self.gate.epoch)
            self.slot.take(0)
            self.report('INPUT_ENABLED' if self.input_enabled else 'INPUT_PAUSED')
        response.success = True
        response.message = 'Waiting for new calibrated captures' if request.data else 'Image ingress paused'
        return response

    def observe_clock(self):
        with self.lock:
            now, wall = self.get_clock().now().nanoseconds/1e9, time.monotonic()
            epoch = self.gate.observe(now, wall)
            if epoch != self.last_epoch:
                self.cache.clear(epoch)
                self.slot.take(0)
                self.last_stamp, self.last_epoch = 0., epoch
                self.report('RESET')
            return now, wall, epoch

    def on_info(self, msg):
        with self.lock:
            _, _, epoch = self.observe_clock()
            previous = self.cache.calibration_id
            try:
                self.cache.add_info(msg, epoch)
            except ValueError:
                self.report('INVALID_CALIBRATION')
            if previous != self.cache.calibration_id:
                self.slot.take(0)

    def on_rgb(self, msg):
        received_ns = time.monotonic_ns() if self.trace.enabled else None
        with self.lock:
            self.input_event(msg, 'INPUT_RECEIVED', received_ns=received_ns)
            if not self.input_enabled:
                self.input_event(msg, 'INPUT_REJECTED', reason='INPUT_PAUSED')
                return
            now, _, epoch = self.observe_clock()
            try:
                self.cache.add_rgb(msg, epoch)
                stamp = seconds(msg.header.stamp)
                candidates = [s for s in self.cache.info if -.03 <= stamp-s <= 1.]
                if not candidates:
                    self.report('NO_FRESH_CALIBRATION')
                    self.input_event(msg, 'INPUT_REJECTED', reason='NO_FRESH_CALIBRATION')
                    return
                info_stamp = min(candidates, key=lambda s: (abs(stamp-s), s))
                k = self.cache.info[info_stamp]
                if msg.header.frame_id != k.frame_id or (msg.width, msg.height) != (k.width, k.height):
                    self.report('CALIBRATION_MISMATCH')
                    self.input_event(msg, 'INPUT_REJECTED', reason='CALIBRATION_MISMATCH')
                    return
                image, receipt = self.cache.rgb[stamp]
                trace_times = (dict(rgb_receive=received_ns, slot_put=time.monotonic_ns())
                               if self.trace.enabled else None)
                job = DetectionJob(image, stamp, epoch, k.calibration_id, info_stamp, receipt, now,
                                   trace_times)
                reason = self.invalid_reason(job)
                if reason is None:
                    self.slot.replace(job)
                    self.report('QUEUED', job=job)
                else:
                    self.input_event(msg, 'INPUT_REJECTED', reason=reason)
            except (ValueError, RuntimeError):
                self.report('INVALID_IMAGE')
                self.input_event(msg, 'INPUT_REJECTED', reason='INVALID_IMAGE')

    def input_event(self, image, status, **details):
        """Bounded capture-linked evidence, including frames never put in a slot."""
        if not self.trace.enabled or self.input_events >= 20000:
            return
        self.input_events += 1
        self.report(status, run_id=self.trace.run_id, sequence=self.input_events,
                    capture_ns=image.header.stamp.sec*1_000_000_000+image.header.stamp.nanosec,
                    source_frame=image.header.frame_id, monotonic_ns=time.monotonic_ns(),
                    ros_now_ns=self.get_clock().now().nanoseconds, **details)

    def current(self, job):
        return self.invalid_reason(job) is None

    def invalid_reason(self, job):
        with self.lock:
            now, wall, epoch = self.observe_clock()
            cached = self.cache.rgb.get(job.stamp)
            if not self.input_enabled or self.stopping.is_set():
                return 'INPUT_PAUSED_OR_STOPPING'
            if job.epoch != epoch:
                return 'EPOCH_CHANGED'
            if job.calibration_id != self.cache.calibration_id:
                return 'CALIBRATION_CHANGED'
            if cached is None or cached[0] is not job.image:
                return 'FRAME_EVICTED'
            if job.stamp <= self.last_stamp:
                return 'OLD_CAPTURE'
            if not -.03 <= now-job.info_stamp <= 1.:
                return 'CALIBRATION_AGE'
            if now-job.stamp < -self.gate.future_slop:
                return 'FUTURE_CAPTURE'
            if not self.gate.valid(job.stamp, job.epoch, now, wall, job.receipt_wall):
                return 'CLOCK_OR_CAPTURE_AGE'
            return None

    def work(self):
        last_start = 0.
        while not self.stopping.is_set():
            # Wait BEFORE taking the slot so only the newest waiting frame is used.
            if self.stopping.wait(max(0., last_start + 1/self.rate - time.monotonic())):
                break
            job = self.slot.take(.1)
            if job is None:
                continue
            trace_times = dict(job.trace_times or {})
            if self.trace.enabled:
                trace_times['work_take'] = time.monotonic_ns()
            if not self.current(job):
                if self.trace.enabled:
                    self.trace.emit('detector', source_frame=job.image.header.frame_id,
                        capture_ns=job.image.header.stamp.sec*1_000_000_000+job.image.header.stamp.nanosec,
                        local_epoch=job.epoch, times_ns=trace_times, outcome='STALE_AT_TAKE',
                        ros_now_ns=self.get_clock().now().nanoseconds)
                continue
            last_start = time.monotonic()
            timing = dict(queue_s=last_start-job.receipt_wall)
            outcome, ros_now_ns = 'BACKEND_ERROR', None
            try:
                if self.trace.enabled:
                    trace_times['convert_start'] = time.monotonic_ns()
                bgr = self.bridge.imgmsg_to_cv2(job.image, 'bgr8')
                if self.trace.enabled:
                    trace_times['convert_end'] = time.monotonic_ns()
                timing['conversion_s'] = time.monotonic()-last_start
                if self.stopping.wait(self.delay):
                    outcome = 'STOPPED'
                    break
                if not self.current(job):
                    outcome = 'EXPIRED_BEFORE_INFERENCE'
                    self.report('EXPIRED_BEFORE_INFERENCE', job=job, **timing)
                    continue
                inference_start = time.monotonic()
                if self.trace.enabled:
                    trace_times['inference_start'] = time.monotonic_ns()
                boxes = [v for v in self.backend.detect(bgr) if v.score >= self.confidence]
                if self.trace.enabled:
                    trace_times['inference_end'] = time.monotonic_ns()
                timing['inference_s'] = time.monotonic()-inference_start
                with self.lock:
                    if self.current(job):
                        message = to_detection_array(boxes, job.image.header,
                            image_size=(job.image.width, job.image.height))
                        if self.trace.enabled:
                            trace_times['publish_start'] = time.monotonic_ns()
                        self.pub.publish(message)
                        if self.trace.enabled:
                            trace_times['publish_end'] = time.monotonic_ns()
                            ros_now_ns = self.get_clock().now().nanoseconds
                        outcome = 'PUBLISHED'
                        self.last_stamp = job.stamp
                        self.report('DETECTED' if boxes else 'EMPTY', job=job, **timing)
                    elif not self.stopping.is_set():
                        outcome = 'EXPIRED_AFTER_INFERENCE'
                        self.report('EXPIRED_AFTER_INFERENCE', job=job, **timing)
            except Exception as exc:
                self.get_logger().error(f'detector backend failed without fallback: {exc!r}')
                self.report('BACKEND_ERROR')
            finally:
                if self.trace.enabled:
                    self.trace.emit('detector', source_frame=job.image.header.frame_id,
                        capture_ns=job.image.header.stamp.sec*1_000_000_000+job.image.header.stamp.nanosec,
                        local_epoch=job.epoch, times_ns=trace_times, outcome=outcome,
                        ros_now_ns=ros_now_ns if ros_now_ns is not None else self.get_clock().now().nanoseconds)

    def destroy_node(self):
        with self.lock:
            self.stopping.set()
            self.slot.close()
        self.worker.join(timeout=5)
        if self.worker.is_alive():
            raise RuntimeError('inference worker did not stop before ROS destruction')
        self.trace.close()
        return super().destroy_node()


def main(args=None):
    from .execution import run_node
    run_node(ObjectDetector, args=args, executor_factory=SingleThreadedExecutor)
