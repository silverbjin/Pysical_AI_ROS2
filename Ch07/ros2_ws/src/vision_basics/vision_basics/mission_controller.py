#!/usr/bin/env python3
"""Ch07 section 7.7 guarded demonstration of detection-based pick/place.

Safety contract: no motion by default. Input is *metric* PointStamped in
base_link from 7.5, not raw /camera/target_pixel (pixel units). Physical grasp
requires an independent fresh /gripper/grasp_verified Boolean before lifting.
"""
import math
import threading
import time

import rclpy
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import PointStamped
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint
from moveit_msgs.srv import GetPositionIK
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import Bool
from trajectory_msgs.msg import JointTrajectoryPoint


class MissionController(Node):
    JOINTS = ('joint1', 'joint2', 'joint3', 'joint4', 'joint_wrist')

    def __init__(self):
        super().__init__('mission_controller')
        self.declare_parameter('enable_motion', False)
        self.declare_parameter('max_target_age_sec', 0.5)
        self.declare_parameter('server_timeout_sec', 5.0)
        self.declare_parameter('action_timeout_sec', 30.0)
        self.motion_enabled = bool(self.get_parameter('enable_motion').value)
        self.max_age = float(self.get_parameter('max_target_age_sec').value)
        self.server_timeout = float(self.get_parameter('server_timeout_sec').value)
        self.action_timeout = float(self.get_parameter('action_timeout_sec').value)
        if min(self.max_age, self.server_timeout, self.action_timeout) <= 0:
            raise ValueError('all timeouts must be positive')
        self.triggered = False  # one-shot; restart node to re-arm
        self.status = 'IDLE'
        self.grasp_ok_at = None
        self.create_subscription(PointStamped, '/robot/target_position',
                                 self.receive_target, 10)
        self.create_subscription(Bool, '/gripper/grasp_verified',
                                 self.receive_grasp_evidence, 10)
        self.ik = self.create_client(GetPositionIK, '/compute_ik')
        self.move_group = ActionClient(self, MoveGroup, '/move_action')
        self.gripper = ActionClient(
            self, FollowJointTrajectory,
            '/gripper_group_controller/follow_joint_trajectory')
        self.get_logger().info(
            'Mission armed: enable_motion=%s; physical grasp verification required'
            % self.motion_enabled)

    def receive_grasp_evidence(self, msg):
        # A Bool-only topic does not attest hardware provenance; simulation-only.
        if msg.data:
            self.grasp_ok_at = time.monotonic()
        else:
            self.grasp_ok_at = None

    def receive_target(self, msg):
        if self.triggered:
            return
        if msg.header.frame_id != 'base_link':
            self.get_logger().warning('Reject target: expected base_link metric frame')
            return
        p = msg.point
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            return
        if not (0.1 <= p.x <= 1.5 and abs(p.y) <= 1.0 and 0.02 <= p.z <= 1.4):
            self.get_logger().warning('Reject target outside educational workspace')
            return
        stamp = Time.from_msg(msg.header.stamp)
        age = (self.get_clock().now() - stamp).nanoseconds / 1e9
        if stamp.nanoseconds == 0 or age < -0.1 or age > self.max_age:
            self.get_logger().warning('Reject target: invalid/stale stamp')
            return
        self.triggered = True
        if not self.motion_enabled:
            self.status = 'HELD'
            self.get_logger().warning(
                'Validated target; motion DISABLED. Enable only after dry-run and collision checks.')
            return
        self.status = 'STARTING'
        worker = threading.Thread(
            target=self.execute, args=(p.x, p.y, p.z), daemon=True)
        worker.start()

    def await_future(self, future, label):
        deadline = time.monotonic() + self.action_timeout
        while rclpy.ok() and not future.done():
            if time.monotonic() > deadline:
                raise TimeoutError(label + ' timed out')
            time.sleep(0.02)
        if not future.done():
            raise RuntimeError(label + ': ROS shutdown')
        value = future.result()
        if value is None:
            raise RuntimeError(label + ': null result')
        return value

    def require_servers(self):
        if not self.ik.wait_for_service(timeout_sec=self.server_timeout):
            raise TimeoutError('/compute_ik unavailable')
        if not self.move_group.wait_for_server(timeout_sec=self.server_timeout):
            raise TimeoutError('/move_action unavailable')
        if not self.gripper.wait_for_server(timeout_sec=self.server_timeout):
            raise TimeoutError('gripper action unavailable')

    def move_arm(self, x, y, z):
        request = GetPositionIK.Request()
        request.ik_request.group_name = 'arm_group'
        request.ik_request.avoid_collisions = True
        request.ik_request.pose_stamped.header.frame_id = 'base_link'
        pose = request.ik_request.pose_stamped.pose
        pose.position.x, pose.position.y, pose.position.z = x, y, z
        pose.orientation.y = 0.70710678
        pose.orientation.w = 0.70710678
        response = self.await_future(self.ik.call_async(request), 'IK')
        if response.error_code.val != 1:
            raise RuntimeError('IK failed: %s' % response.error_code.val)
        mapping = dict(zip(response.solution.joint_state.name,
                           response.solution.joint_state.position))
        if any(j not in mapping for j in self.JOINTS):
            raise RuntimeError('IK omitted required arm joints')
        goal = MoveGroup.Goal()
        goal.request.group_name = 'arm_group'
        goal.request.allowed_planning_time = 5.0
        goal.request.num_planning_attempts = 5
        goal.planning_options.plan_only = False
        goal.planning_options.replan = False
        constraints = Constraints()
        for joint in self.JOINTS:
            jc = JointConstraint()
            jc.joint_name = joint
            jc.position = float(mapping[joint])
            jc.tolerance_above = 0.02
            jc.tolerance_below = 0.02
            jc.weight = 1.0
            constraints.joint_constraints.append(jc)
        goal.request.goal_constraints.append(constraints)
        handle = self.await_future(self.move_group.send_goal_async(goal), 'move acceptance')
        if not handle.accepted:
            raise RuntimeError('MoveGroup rejected goal')
        result = self.await_future(handle.get_result_async(), 'move execution')
        if result.status != 4 or result.result.error_code.val != 1:
            raise RuntimeError('MoveGroup failed: status=%s' % result.status)

    def move_gripper(self, position_m):
        if not 0.0 <= position_m <= 0.025:
            raise ValueError('Finger position out of URDF limits')
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ['joint_finger1', 'joint_finger2']
        point = JointTrajectoryPoint()
        point.positions = [position_m, position_m]
        point.time_from_start.sec = 1
        goal.trajectory.points = [point]
        handle = self.await_future(self.gripper.send_goal_async(goal), 'gripper acceptance')
        if not handle.accepted:
            raise RuntimeError('Gripper rejected goal')
        result = self.await_future(handle.get_result_async(), 'gripper result')
        if result.status != 4 or result.result.error_code != 0:
            raise RuntimeError('Gripper action failed')

    def execute(self, x, y, z):
        try:
            self.require_servers()
            self.status = 'APPROACH'
            self.move_gripper(0.0)  # open
            self.move_arm(x, y, z + 0.15)
            self.status = 'DESCEND'
            self.move_arm(x, y, z + 0.03)
            self.status = 'GRASP'
            self.grasp_ok_at = None  # evidence must be NEW after close
            self.move_gripper(0.02)  # close
            deadline = time.monotonic() + 3.0
            while rclpy.ok() and time.monotonic() < deadline:
                if self.grasp_ok_at is not None:
                    break
                time.sleep(0.02)
            if self.grasp_ok_at is None:
                raise RuntimeError('No fresh grasp verification: STOP before lift')
            self.status = 'LIFT'
            self.move_arm(x, y, z + 0.20)
            self.status = 'PLACE'
            self.move_arm(0.4, -0.25, 0.4)  # configured educational bin pose
            self.move_gripper(0.0)
            self.status = 'COMMAND_SEQUENCE_DONE'
            self.get_logger().warning(
                'Command sequence finished; OBJECT PLACEMENT NOT VERIFIED.')
        except Exception as exc:
            self.status = 'FAILED'
            self.get_logger().error('Mission halted at stage: ' + str(exc))
        # Deliberately never re-arm from a persistent target.


def main(args=None):
    rclpy.init(args=args)
    node = MissionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
