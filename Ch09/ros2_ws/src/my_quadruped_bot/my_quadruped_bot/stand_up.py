"""Ch09 stand_up: smoothly transition from observed joint angles to stand pose.

ROS 2 Jazzy / Gazebo Harmonic simulation demonstration. This does not replace
physical robot stability monitoring or emergency stop.
"""
import math
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64


class StandUpNode(Node):
    # A six-second smoothstep was selected from controlled Gazebo A/B evidence.
    RAMP_DURATION_S = 6.0

    def __init__(self):
        super().__init__('stand_up_node')

        # Preserve the original guide's final pose and command topic names.
        self.target_pose = {'hip': 0.0, 'thigh': -0.6, 'calf': 1.2}
        legs = ('fr', 'fl', 'rr', 'rl')
        kinds = ('hip', 'thigh', 'calf')
        self.joints = [f'{leg}_{kind}' for leg in legs for kind in kinds]

        self.targets = {
            joint: self.target_pose[joint.split('_')[1]]
            for joint in self.joints
        }
        self.pubs = {
            joint: self.create_publisher(
                Float64, f'/model/my_quadruped/joint/{joint}_joint/cmd_pos', 10
            )
            for joint in self.joints
        }

        self.initial_positions = None
        self.ramp_start = None
        self.wait_start = time.monotonic()
        self.reported_missing = False
        self.reported_complete = False

        # Observe the *actual* current posture before the first command.
        # Avoid an abrupt 0 -> target setpoint that tips the quadruped backward.
        self.joint_state_sub = self.create_subscription(
            JointState, '/joint_states', self.on_joint_states, 10
        )
        self.timer = self.create_timer(0.1, self.publish_callback)
        self.get_logger().info(
            'Stand Up Node started; waiting for all 12 measured joint positions'
        )

    def on_joint_states(self, msg):
        if self.initial_positions is not None:
            return

        measured = dict(zip(msg.name, msg.position))
        names = [f'{joint}_joint' for joint in self.joints]
        if not all(
            name in measured and math.isfinite(measured[name])
            for name in names
        ):
            return

        self.initial_positions = {
            joint: float(measured[f'{joint}_joint'])
            for joint in self.joints
        }
        self.ramp_start = time.monotonic()
        self.get_logger().info('STAND_UP_MEASURED_START_RAMP_6S')

    def publish_callback(self):
        if self.initial_positions is None:
            if not self.reported_missing and time.monotonic() - self.wait_start >= 8.0:
                self.get_logger().error(
                    'STAND_UP_NO_JOINT_STATES_NO_COMMAND: '
                    'check ros_gz_bridge and /joint_states'
                )
                self.reported_missing = True
            return

        fraction = min(1.0, max(
            0.0, (time.monotonic() - self.ramp_start) / self.RAMP_DURATION_S
        ))
        blend = fraction * fraction * (3.0 - 2.0 * fraction)

        for joint, pub in self.pubs.items():
            initial = self.initial_positions[joint]
            goal = self.targets[joint]
            msg = Float64()
            msg.data = initial + (goal - initial) * blend
            pub.publish(msg)

        if fraction >= 1.0 and not self.reported_complete:
            self.reported_complete = True
            self.get_logger().info('STAND_UP_RAMP_COMPLETE_ORIGINAL_GOALS')


def main(args=None):
    rclpy.init(args=args)
    node = StandUpNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Stand Up Node...')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
