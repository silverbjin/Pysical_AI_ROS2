"""One inference worker, one newest waiting frame, original capture headers."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from threading import Event, RLock, Thread
import time

from cv_bridge import CvBridge
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from std_srvs.srv import SetBool
from vision_msgs.msg import Detection2DArray

from .cache import RGBDCache, seconds
from .detectors import ColorFixtureBackend, YoloBackend, to_detection_array
from .freshness import ClockGate, LatestSlot


@dataclass(frozen=True)
class DetectionJob:
    image: object
    stamp: float
    epoch: int
    calibration_id: str
    info_stamp: float
    receipt_wall: float


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
                or not 0 < self.rate <= 10 or self.delay < 0 or not .5 <= self.confidence <= 1):
            raise ValueError('rate in (0,10], nonnegative delay, confidence in [.5,1] required')
        if self.backend_name == 'yolo':
            if not weights or not Path(weights).is_absolute():
                raise FileNotFoundError('YOLO requires an explicit absolute local weights_path')
            self.backend = YoloBackend(Path(weights), expected_sha256=expected_sha or None)
        elif self.backend_name == 'color_fixture':
            self.backend = ColorFixtureBackend()
        else:
            raise ValueError('backend must be yolo or color_fixture; no fallback')
        self.bridge = CvBridge()
        self.lock, self.stopping = RLock(), Event()
        self.gate, self.cache, self.slot = ClockGate(), RGBDCache(), LatestSlot()
        self.last_epoch, self.last_stamp = -1, 0.
        self.input_enabled = True
        self.input_service = self.create_service(SetBool, '~/set_input_enabled', self.set_input_enabled)
        self.pub = self.create_publisher(Detection2DArray, '/vision/detections', qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, '/vision/detector_status', 10)
        self.rgb_sub = self.create_subscription(Image, '/camera/color/image_raw', self.on_rgb,
                                                 qos_profile_sensor_data)
        self.info_sub = self.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info,
                                                  qos_profile_sensor_data)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.watchdog = self.create_timer(.05, self.observe_clock, clock=self.steady_clock)
        self.worker = Thread(target=self.work, name='detector-inference', daemon=False)
        self.get_logger().info(f'explicit detector backend={self.backend_name}, max_rate_hz={self.rate}')
        self.worker.start()  # last constructor operation; no fallible setup after start

    def report(self, reason):
        if not self.stopping.is_set():
            msg = String()
            msg.data = json.dumps({'backend': self.backend_name, 'status': reason, 'epoch': self.gate.epoch})
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
        with self.lock:
            if not self.input_enabled:
                return
            _, _, epoch = self.observe_clock()
            try:
                self.cache.add_rgb(msg, epoch)
                stamp = seconds(msg.header.stamp)
                candidates = [s for s in self.cache.info if -.03 <= stamp-s <= 1.]
                if not candidates:
                    self.report('NO_FRESH_CALIBRATION')
                    return
                info_stamp = min(candidates, key=lambda s: (abs(stamp-s), s))
                k = self.cache.info[info_stamp]
                if msg.header.frame_id != k.frame_id or (msg.width, msg.height) != (k.width, k.height):
                    self.report('CALIBRATION_MISMATCH')
                    return
                image, receipt = self.cache.rgb[stamp]
                job = DetectionJob(image, stamp, epoch, k.calibration_id, info_stamp, receipt)
                if self.current(job):
                    self.slot.replace(job)
            except (ValueError, RuntimeError):
                self.report('INVALID_IMAGE')

    def current(self, job):
        with self.lock:
            now, wall, epoch = self.observe_clock()
            cached = self.cache.rgb.get(job.stamp)
            return (self.input_enabled and not self.stopping.is_set() and job.epoch == epoch
                    and job.calibration_id == self.cache.calibration_id
                    and cached is not None and cached[0] is job.image
                    and job.stamp > self.last_stamp and -.03 <= now-job.info_stamp <= 1.
                    and self.gate.valid(job.stamp, job.epoch, now, wall, job.receipt_wall))

    def work(self):
        last_start = 0.
        while not self.stopping.is_set():
            # Wait BEFORE taking the slot so only the newest waiting frame is used.
            if self.stopping.wait(max(0., last_start + 1/self.rate - time.monotonic())):
                break
            job = self.slot.take(.1)
            if job is None or not self.current(job):
                continue
            last_start = time.monotonic()
            try:
                bgr = self.bridge.imgmsg_to_cv2(job.image, 'bgr8')
                if self.stopping.wait(self.delay):
                    break
                if not self.current(job):
                    self.report('EXPIRED_BEFORE_INFERENCE')
                    continue
                boxes = [v for v in self.backend.detect(bgr) if v.score >= self.confidence]
                with self.lock:
                    if self.current(job):
                        self.pub.publish(to_detection_array(boxes, job.image.header,
                                                            image_size=(job.image.width, job.image.height)))
                        self.last_stamp = job.stamp
                        self.report('DETECTED' if boxes else 'EMPTY')
                    elif not self.stopping.is_set():
                        self.report('EXPIRED_AFTER_INFERENCE')
            except Exception as exc:
                self.get_logger().error(f'detector backend failed without fallback: {exc!r}')
                self.report('BACKEND_ERROR')

    def destroy_node(self):
        with self.lock:
            self.stopping.set()
            self.slot.close()
        self.worker.join(timeout=5)
        if self.worker.is_alive():
            raise RuntimeError('inference worker did not stop before ROS destruction')
        return super().destroy_node()


def main(args=None):
    from .execution import run_node
    run_node(ObjectDetector, args=args, executor_factory=SingleThreadedExecutor)
