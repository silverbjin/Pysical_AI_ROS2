#!/usr/bin/env python3
"""카운트다운 액션 클라이언트: 결과/거절/서버 부재에서 모두 종료한다."""
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from my_robot_interfaces.action import CountUntil


class CountUntilClient(Node):
    def __init__(self):
        super().__init__('count_until_client')
        self._action_client = ActionClient(self, CountUntil, 'count_until')
        self.finished = False
        self.success = False

    def send_goal(self, target, period):
        goal_msg = CountUntil.Goal(target_number=target, period=period)
        self.get_logger().info('Waiting for action server (up to 5 s)...')
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Action server unavailable')
            self.finished = True
            return
        self.get_logger().info('Sending goal...')
        future = self._action_client.send_goal_async(
            goal_msg, feedback_callback=self.feedback_callback)
        future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
        except Exception as exc:
            self.get_logger().error(f'Goal request failed: {exc}')
            self.finished = True
            return
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected')
            self.finished = True
            return
        self.get_logger().info('Goal accepted! Waiting for result...')
        future = goal_handle.get_result_async()
        future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        self.get_logger().info(
            f'>>> Feedback received: {feedback_msg.feedback.current_number}')

    def get_result_callback(self, future):
        try:
            wrapped = future.result()
            self.get_logger().info(
                f'Result received: {wrapped.result.reached_number}, status={wrapped.status}')
            from action_msgs.msg import GoalStatus
            self.success = wrapped.status == GoalStatus.STATUS_SUCCEEDED
        except Exception as exc:
            self.get_logger().error(f'Failed to receive result: {exc}')
        finally:
            self.finished = True


def main(args=None):
    rclpy.init(args=args)
    node = CountUntilClient()
    try:
        node.send_goal(5, 0.5)
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
