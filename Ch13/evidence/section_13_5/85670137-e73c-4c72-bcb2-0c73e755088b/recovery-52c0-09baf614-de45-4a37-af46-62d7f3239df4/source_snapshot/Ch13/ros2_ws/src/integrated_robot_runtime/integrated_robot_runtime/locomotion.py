"""50 Hz stand reference publisher; no PPO policy or WALK mode is claimed."""
import json
import threading
import time

from integrated_robot_interfaces.srv import SetMode
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray, String

from .common import seconds, spin
from .policy import ARM_NAMES, LEG_NAMES, STAND, joint_snapshot, safe_arm


class LocomotionNode(LifecycleNode):
    def __init__(self):
        super().__init__('locomotion_node')
        self.lock = threading.RLock()
        self.enabled = False
        self.mode = 'STOP'
        self.legs = self.arm = None
        self.received = 0.0
        self.stamp = 0.0
        self.command_count = 0
        self.last_tick = None
        self.max_gap = 0.0
        self.control_group = MutuallyExclusiveCallbackGroup()
        self.input_group = MutuallyExclusiveCallbackGroup()
        self.command = self.create_publisher(
            Float64MultiArray, '/leg_position_controller/commands', 1)
        self.status = self.create_publisher(String, '/architecture/locomotion', 10)
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10,
                                 callback_group=self.input_group)
        self.create_service(SetMode, '~/set_mode', self.set_mode,
                            callback_group=self.control_group)
        self.create_timer(0.02, self.tick, callback_group=self.control_group)
        self.create_timer(0.2, self.report, callback_group=self.input_group)

    def on_joints(self, msg):
        with self.lock:
            self.legs = joint_snapshot(msg.name, msg.position, LEG_NAMES)
            self.arm = joint_snapshot(msg.name, msg.position, ARM_NAMES)
            self.received = time.monotonic()
            self.stamp = seconds(msg.header.stamp)

    def ready(self):
        age = time.monotonic() - self.received
        ros_age = self.get_clock().now().nanoseconds * 1e-9 - self.stamp
        return (self.legs is not None and safe_arm(self.arm, age)
                and self.stamp > 0 and -0.05 <= ros_age <= 0.5)

    def on_configure(self, state):
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        with self.lock:
            if not self.ready():
                return TransitionCallbackReturn.FAILURE
            self.start = list(self.legs)
            self.started = time.monotonic()
            self.enabled = True
            self.mode = 'STAND'
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state):
        with self.lock:
            self.enabled = False
            self.mode = 'STOP'
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state):
        return self.on_deactivate(state)

    def on_shutdown(self, state):
        return self.on_deactivate(state)

    def set_mode(self, request, response):
        with self.lock:
            if request.mode not in ('STAND', 'HOLD', 'STOP'):
                response.message = 'Unsupported mode; WALK needs a validated locomotion policy'
            elif not self.enabled or not self.ready():
                response.message = 'Node inactive or joint/arm safety gate not ready'
            else:
                self.mode = request.mode
                self.start = list(self.legs)
                self.started = time.monotonic()
                response.accepted = True
                response.message = request.mode
        return response

    def tick(self):
        with self.lock:
            now = time.monotonic()
            if self.last_tick is not None:
                self.max_gap = max(self.max_gap, now - self.last_tick)
            self.last_tick = now
            if not self.enabled or self.mode == 'STOP':
                return
            if not self.ready():
                # Latch STOP until an explicit valid mode request; no auto restart.
                self.mode = 'STOP'
                return
            alpha = min(1.0, (now - self.started) / 2.0)
            values = (self.start if self.mode == 'HOLD' else
                      [a + alpha * (b - a) for a, b in zip(self.start, STAND)])
            self.command.publish(Float64MultiArray(data=list(values)))
            self.command_count += 1

    def report(self):
        with self.lock:
            self.status.publish(String(data=json.dumps({
                'active': self.enabled, 'mode': self.mode, 'ready': self.ready(),
                'command_count': self.command_count, 'max_timer_gap_s': self.max_gap,
                'policy': 'stand_reference_not_ppo',
            })))


def main():
    # All callbacks are bounded and nonblocking; heavy perception is a
    # different process. No synchronous service/action wait belongs here.
    spin(LocomotionNode, threads=1)
