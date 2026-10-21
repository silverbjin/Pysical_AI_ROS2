"""Publish a bounded, one-point joint trajectory for the Ch05 arm."""

import rclpy
from builtin_interfaces.msg import Duration
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


JOINT_NAMES = ['joint1', 'joint2', 'joint3', 'joint4']
BENDING = [0.0, 0.5, 0.5, 1.0]
HOME = [0.0, 0.0, 0.0, 0.0]
JOINT_LIMITS = [(-3.14159, 3.14159), (-1.57079, 1.57079),
                (-2.0944, 2.0944), (-3.14159, 3.14159)]


def validate_goal(values):
    """Reject nonfinite, out-of-range or incomplete joint targets."""
    import math

    if len(values) != len(JOINT_NAMES):
        raise ValueError('expected exactly four joint positions')
    if any(not math.isfinite(v) or not lower <= v <= upper
           for v, (lower, upper) in zip(values, JOINT_LIMITS)):
        raise ValueError('nonfinite or out-of-range joint target')
    return list(values)


class SimpleTrajectoryPublisher(Node):
    """Alternate home/bent positions using zero endpoint velocity."""

    def __init__(self):
        super().__init__('simple_trajectory_publisher')
        self.publisher_ = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.moving_forward = True
        self.timer = self.create_timer(2.0, self.timer_callback)
        self.get_logger().info('Simple Trajectory Publisher Started')

    def timer_callback(self):
        # Do not toggle if the controller is not yet subscribed.
        if self.publisher_.get_subscription_count() == 0:
            self.get_logger().warning('No arm_controller subscriber yet; retrying')
            return
        target = validate_goal(BENDING if self.moving_forward else HOME)
        msg = JointTrajectory()
        msg.joint_names = list(JOINT_NAMES)
        point = JointTrajectoryPoint()
        point.positions = target
        # Position+velocity allows cubic interpolation, unlike position-only
        # trajectories which use linear interpolation in JTC's spline mode.
        point.velocities = [0.0] * len(JOINT_NAMES)
        point.time_from_start = Duration(sec=1, nanosec=0)
        msg.points = [point]
        self.publisher_.publish(msg)
        self.get_logger().info('Goal: Bending Position' if self.moving_forward
                               else 'Goal: Home Position')
        self.moving_forward = not self.moving_forward


def main(args=None):
    rclpy.init(args=args)
    node = SimpleTrajectoryPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
