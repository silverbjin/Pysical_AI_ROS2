"""One explicit launch opt-in, after measured readiness; never auto-re-enable."""
import json
import time

from integrated_robot_interfaces.msg import TrackedTarget
from integrated_robot_vision.cache import nanoseconds
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import SetBool

from .common import spin
from .policy import ARM_NAMES, LEG_NAMES, STAND, joint_snapshot, safe_arm


class TrackingRequester(Node):
    def __init__(self, **kwargs):
        super().__init__('tracking_requester', **kwargs)
        self.startup_ready = False
        self.joints = self.target = None
        self.done, self.success, self.requested = False, False, False
        self.started = time.monotonic()
        self.requested_at = None
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status = self.create_publisher(String, '/architecture/tracking_request', qos)
        self.client = self.create_client(SetBool, '/manipulation_node/set_visual_tracking')
        self.create_subscription(String, '/architecture/startup', self.on_startup, qos)
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10)
        self.create_subscription(TrackedTarget, '/vision/tracked_target', self.on_target, 10)
        self.create_timer(.02, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_startup(self, message):
        try:
            status = json.loads(message.data).get('status')
            self.startup_ready = status == 'READY'
            if status == 'FAILED':
                self.report(False, 'Measured startup failed; no tracking requested')
        except (ValueError, TypeError, AttributeError):
            self.startup_ready = False

    def on_joints(self, message):
        try:
            stamp = nanoseconds(message.header.stamp)
            arm = joint_snapshot(message.name, message.position, ARM_NAMES)
            legs = joint_snapshot(message.name, message.position, LEG_NAMES)
            self.joints = (stamp, time.monotonic(), arm, legs)
        except (ValueError, TypeError):
            self.joints = None

    def on_target(self, message):
        try:
            self.target = (nanoseconds(message.header.stamp), time.monotonic()) if (
                message.valid and message.status == 'TRACKED') else None
        except (ValueError, TypeError):
            self.target = None

    def report(self, success, message):
        if self.done:
            return
        self.done, self.success = True, success
        self.status.publish(String(data=json.dumps(dict(success=success, message=message,
                                                        automatic_retry=False))))
        (self.get_logger().info if success else self.get_logger().error)(message)

    def response(self, future):
        if self.done:
            if not self.success:
                try:
                    if future.result().success:
                        self.client.call_async(SetBool.Request(data=False))
                except Exception as exc:
                    self.get_logger().error('Late tracking enable/cancel state unknown: '+str(exc))
            return
        try:
            reply = future.result()
            self.report(reply.success, reply.message)
        except Exception as exc:
            self.report(False, 'Tracking request failed: '+str(exc))

    def tick(self):
        if self.done:
            return
        wall, now = time.monotonic(), self.get_clock().now().nanoseconds
        if wall-self.started > 30. or (self.requested_at is not None and wall-self.requested_at > 5.):
            if self.requested:
                self.client.call_async(SetBool.Request(data=False))
            self.report(False, 'Tracking opt-in deadline exceeded; no automatic retry')
            return
        if self.requested or not self.startup_ready or self.joints is None or self.target is None:
            return
        stamp, received, arm, legs = self.joints
        target_stamp, target_received = self.target
        if (stamp <= 0 or target_stamp <= 0 or not safe_arm(arm, wall-received)
                or legs is None or not all(abs(a-b) <= .15 for a, b in zip(legs, STAND))
                or not 0 <= wall-received <= .3 or not 0 <= now-stamp <= .3e9
                or not 0 <= wall-target_received <= .3 or not 0 <= now-target_stamp <= .2e9
                or not self.client.service_is_ready()):
            return
        self.requested, self.requested_at = True, wall
        try:
            self.client.call_async(SetBool.Request(data=True)).add_done_callback(self.response)
        except Exception as exc:
            self.report(False, str(exc))


def main():
    spin(TrackingRequester)
