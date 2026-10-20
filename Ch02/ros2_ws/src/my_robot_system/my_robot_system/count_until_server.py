#!/usr/bin/env python3
"""카운트다운 액션 서버: 취소 가능한 장기 실행 태스크의 교육용 예제."""
import math
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from my_robot_interfaces.action import CountUntil


class CountUntilServer(Node):
    def __init__(self):
        super().__init__('count_until_server')
        # 기본 MutuallyExclusiveCallbackGroup을 쓰면 멀티스레드만으로
        # 취소 콜백의 병렬 실행을 보장할 수 없다.
        self.callback_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self, CountUntil, 'count_until',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group,
        )
        self.get_logger().info('Action Server has been started.')

    def goal_callback(self, goal_request):
        target = goal_request.target_number
        period = goal_request.period
        if not 1 <= target <= 1000 or not math.isfinite(period) or not 0.01 <= period <= 10.0:
            self.get_logger().warn('Rejecting goal: target must be 1..1000, period 0.01..10 s')
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Received cancel request')
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        result = CountUntil.Result()
        feedback_msg = CountUntil.Feedback()
        period = goal_handle.request.period
        target = goal_handle.request.target_number
        count = 0

        for _ in range(target):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result.reached_number = count
                self.get_logger().info(f'Goal canceled at {count}')
                return result

            count += 1
            feedback_msg.current_number = count
            goal_handle.publish_feedback(feedback_msg)
            self.get_logger().info(f'Counting... {count}')
            # 작은 지연 구간으로 나누어 취소 반영 시간을 짧게 유지한다.
            end_time = time.monotonic() + period
            while time.monotonic() < end_time:
                if goal_handle.is_cancel_requested:
                    goal_handle.canceled()
                    result.reached_number = count
                    self.get_logger().info(f'Goal canceled at {count}')
                    return result
                time.sleep(min(0.05, max(0.0, end_time - time.monotonic())))

        goal_handle.succeed()
        result.reached_number = count
        self.get_logger().info(f'Goal succeeded. Result: {count}')
        return result


def main(args=None):
    rclpy.init(args=args)
    node = CountUntilServer()
    executor = MultiThreadedExecutor(num_threads=2)
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
