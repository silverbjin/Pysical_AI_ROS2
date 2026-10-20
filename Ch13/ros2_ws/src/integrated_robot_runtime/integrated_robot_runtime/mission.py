"""Explicit operator-triggered action client; preserves unsupported task failure."""
from integrated_robot_interfaces.action import PickObject
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from std_srvs.srv import Trigger

from .common import spin, wait_future


class MissionCommander(Node):
    def __init__(self):
        super().__init__('mission_commander')
        self.group = ReentrantCallbackGroup()
        self.client = ActionClient(self, PickObject, '/manipulation_node/pick_object',
                                   callback_group=self.group)
        self.create_service(Trigger, '~/rehearse_pick', self.rehearse,
                            callback_group=self.group)

    def rehearse(self, request, response):
        handle = None
        try:
            if not self.client.wait_for_server(timeout_sec=3):
                raise TimeoutError('PickObject server unavailable')
            goal = PickObject.Goal()
            goal.object_name = 'demo_cup'
            goal.dry_run = True
            goal.target_pose.header.frame_id = 'base_link'
            goal.target_pose.header.stamp = self.get_clock().now().to_msg()
            goal.target_pose.pose.position.x = 0.3
            goal.target_pose.pose.position.z = 0.4
            goal.target_pose.pose.orientation.w = 1.0
            handle = wait_future(self.client.send_goal_async(goal), 3)
            if not handle.accepted:
                raise RuntimeError('PickObject rejected: inspect readiness/target age')
            wrapped = wait_future(handle.get_result_async(), 5)
            response.success = wrapped.result.success
            response.message = wrapped.result.message
        except Exception as exc:
            if handle is not None and handle.accepted:
                handle.cancel_goal_async()
            response.message = str(exc)
        return response


def main():
    spin(MissionCommander)
