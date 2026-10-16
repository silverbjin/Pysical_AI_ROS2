"""Queue scans briefly for acquisition-time TF, reject excessive sensor tilt."""
from collections import Counter, deque
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformException, TransformListener
from my_quadruped_bot.sensors.scan_gate import ScanGate


class SlamScanFilter(Node):
    def __init__(self, node_name='slam_scan_filter', output_default='/scan/slam'):
        super().__init__(node_name)
        descriptor = ParameterDescriptor(read_only=True)
        defaults = {'input_topic': '/scan', 'output_topic': output_default,
                    'reference_frame': 'odom', 'expected_scan_frame': 'lidar_link',
                    'max_tilt_degrees': 5.0, 'min_scan_interval': 0.15,
                    'max_scan_age': 0.5}
        for key, value in defaults.items():
            self.declare_parameter(key, value, descriptor)
        get = lambda name: self.get_parameter(name).value
        self.reference_frame = get('reference_frame')
        self.expected_frame = get('expected_scan_frame')
        if get('input_topic') == get('output_topic'):
            raise ValueError('Input and output scan topics must differ')
        self.gate = ScanGate(get('max_tilt_degrees'), get('min_scan_interval'), get('max_scan_age'))
        self.buffer = Buffer(cache_time=Duration(seconds=30), node=self)
        self.listener = TransformListener(self.buffer, self)
        self.queue = deque()
        self.counts = Counter()
        self.last_now = None
        self.pub = self.create_publisher(LaserScan, get('output_topic'), qos_profile_sensor_data)
        self.sub = self.create_subscription(LaserScan, get('input_topic'), self.receive, qos_profile_sensor_data)
        self.timer = self.create_timer(0.02, self.flush)
        self.report_timer = self.create_timer(5.0, self.report)

    @staticmethod
    def stamp_ns(msg):
        return msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec

    def receive(self, msg):
        if msg.header.frame_id != self.expected_frame or not msg.ranges or self.stamp_ns(msg) <= 0:
            self.counts['invalid_message'] += 1
            return
        if len(self.queue) >= 5:
            self.queue.popleft()
            self.counts['queue_overflow'] += 1
        self.queue.append(msg)
        self.flush()

    def flush(self):
        now_ns = self.get_clock().now().nanoseconds
        if self.last_now is not None and now_ns < self.last_now:
            self.queue.clear()
            self.gate.last_accepted_ns = None
            self.counts['clock_reset'] += 1
        self.last_now = now_ns
        while self.queue:
            msg = self.queue[0]
            stamp_ns = self.stamp_ns(msg)
            if now_ns - stamp_ns > self.gate.max_age_ns or stamp_ns - now_ns > self.gate.future_ns:
                self.queue.popleft()
                self.counts['stale_or_future'] += 1
                continue
            q = self.rotation_at(msg)
            if q is None:
                return
            self.queue.popleft()
            result = self.gate.check(stamp_ns, now_ns, q)
            self.counts[result] += 1
            if result == 'accepted':
                self.pub.publish(msg)  # Preserve stamp, frame, angles and ranges verbatim.

    def rotation_at(self, msg):
        try:
            tf = self.buffer.lookup_transform(self.reference_frame, msg.header.frame_id,
                                              Time.from_msg(msg.header.stamp))
        except TransformException:
            return None
        q = tf.transform.rotation
        return (q.x, q.y, q.z, q.w)

    def report(self):
        self.get_logger().info(f'SLAM scan gate: {dict(self.counts)}, pending={len(self.queue)}')


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SlamScanFilter()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
