#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from my_robot_interfaces.action import CountUntil

class CountUntilClient(Node):
    def __init__(self):
        super().__init__('count_until_client')
        self._action_client = ActionClient(self, CountUntil, 'count_until')

    def send_goal(self, target, period):
        goal_msg = CountUntil.Goal()
        goal_msg.target_number = target
        goal_msg.period = period

        self.get_logger().info('Waiting for action server...')
        self._action_client.wait_for_server()

        # 1. 비동기로 목표 전송
        self.get_logger().info('Sending goal...')
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        
        # 2. 서버가 목표를 수락했는지 확인하는 콜백 등록
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """서버의 수락/거절 응답 처리"""
        goal_handle = future.result()
        
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            return

        self.get_logger().info('Goal accepted! Waiting for result...')
        
        # 3. 최종 결과를 기다리는 콜백 등록
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        """작업 중간에 오는 피드백 처리"""
        number = feedback_msg.feedback.current_number
        self.get_logger().info(f'>>> Feedback received: {number}')

    def get_result_callback(self, future):
        """최종 결과 처리"""
        result = future.result().result
        self.get_logger().info(f'Result received: {result.reached_number}')
        # 작업이 끝났으므로 노드 종료 (선택사항)
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = CountUntilClient()
    
    # 목표: 5까지 0.5초 간격으로 세라
    node.send_goal(5, 0.5)
    
    rclpy.spin(node)

if __name__ == '__main__':
    main()
