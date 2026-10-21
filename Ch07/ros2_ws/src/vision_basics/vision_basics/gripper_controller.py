#!/usr/bin/env python3
"""Ch07 gripper demo: sequential action goals with bounded waits.

joint_finger1/2 are prismatic (metres). Positive travel closes the symmetric
URDF gripper; reaching a goal is NOT proof of physical object grasp.
"""
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionClient
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectoryPoint


class GripperController(Node):
    OPEN_M = 0.0
    CLOSE_M = 0.02  # URDF limit per finger 0..0.025 m

    def __init__(self):
        super().__init__('gripper_controller')
        self.declare_parameter('goal_timeout_sec', 10.0)
        self.declare_parameter('server_timeout_sec', 10.0)
        self.goal_timeout = float(self.get_parameter('goal_timeout_sec').value)
        self.server_timeout = float(self.get_parameter('server_timeout_sec').value)
        if self.goal_timeout <= 0 or self.server_timeout <= 0:
            raise ValueError('timeouts must be positive')
        self.client = ActionClient(
            self, FollowJointTrajectory,
            '/gripper_group_controller/follow_joint_trajectory')
        self.state = 'WAIT_SERVER'
        self.started = time.monotonic()
        self.pending_since = None
        self.timer = self.create_timer(0.1, self.tick)

    def tick(self):
        now = time.monotonic()
        if self.state == 'WAIT_SERVER':
            if self.client.wait_for_server(timeout_sec=0.0):
                self.send_position(self.OPEN_M, 'OPENING')
            elif now - self.started > self.server_timeout:
                self.fail('Action server unavailable (timeout)')
        elif self.state in ('OPENING', 'CLOSING'):
            if self.pending_since is not None and now - self.pending_since > self.goal_timeout:
                self.fail('Action goal/result timeout: ' + self.state)

    def send_position(self, position_m, state):
        if not 0.0 <= position_m <= 0.025:
            raise ValueError('joint travel must be 0..0.025 m')
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ['joint_finger1', 'joint_finger2']
        point = JointTrajectoryPoint()
        point.positions = [float(position_m), float(position_m)]
        point.time_from_start.sec = 1
        goal.trajectory.points = [point]
        self.state = state
        self.pending_since = time.monotonic()
        future = self.client.send_goal_async(goal)
        future.add_done_callback(self.on_accepted)

    def on_accepted(self, future):
        if self.state not in ('OPENING', 'CLOSING'):
            return
        try:
            handle = future.result()
            if handle is None or not handle.accepted:
                self.fail('Goal rejected')
                return
            handle.get_result_async().add_done_callback(self.on_result)
        except Exception as exc:
            self.fail('Goal response failed: ' + str(exc))

    def on_result(self, future):
        if self.state not in ('OPENING', 'CLOSING'):
            return
        try:
            response = future.result()
            if (response is None or response.status != 4
                    or response.result.error_code != 0):
                self.fail('Action execution did not succeed')
                return
            if self.state == 'OPENING':
                self.get_logger().info('Gripper opened (action result only)')
                self.send_position(self.CLOSE_M, 'CLOSING')
            else:
                self.state = 'DONE'
                self.pending_since = None
                self.get_logger().info('Gripper closed (action result only); grasp unverified')
                self.timer.cancel()
        except Exception as exc:
            self.fail('Result handling failed: ' + str(exc))

    def fail(self, message):
        self.get_logger().error(message)
        self.state = 'FAILED'
        self.pending_since = None
        self.timer.cancel()


def main(args=None):
    rclpy.init(args=args)
    node = GripperController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
