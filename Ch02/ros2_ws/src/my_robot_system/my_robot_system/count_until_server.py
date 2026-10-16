#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from my_robot_interfaces.action import CountUntil

class CountUntilServer(Node):
    def __init__(self):
        super().__init__('count_until_server')
        
        # [중요] 액션 서버 생성
        # execute_callback: 목표를 수락했을 때 실제 작업을 수행하는 함수
        # callback_group: 동시에 여러 요청을 처리하거나 취소 명령을 받기 위해 필요
        self._action_server = ActionServer(
            self,
            CountUntil,
            'count_until',
            self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback)
            
        self.get_logger().info('Action Server has been started.')

    def goal_callback(self, goal_request):
        """1. 목표 수신 시 수락 여부 결정"""
        self.get_logger().info(f'Received goal request: {goal_request.target_number}')
        # 예: 목표값이 0 이하면 거절하는 로직을 넣을 수 있다.
        if goal_request.target_number <= 0:
            self.get_logger().warn('Rejecting goal: Target must be positive')
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """2. 취소 요청 수신 시 처리"""
        self.get_logger().info('Received cancel request')
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        """3. 실제 작업 수행 (메인 로직)"""
        self.get_logger().info('Executing goal...')
        
        # 목표 데이터 추출
        target_number = goal_handle.request.target_number
        period = goal_handle.request.period
        
        feedback_msg = CountUntil.Feedback()
        result = CountUntil.Result()
        counter = 0

        # 메인 루프: 목표에 도달할 때까지 반복
        for i in range(target_number):
            # (1) 취소 요청이 들어왔는지 확인
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('Goal canceled')
                result.reached_number = counter
                return result

            # (2) 작업 수행 (여기서는 단순 카운트 및 대기)
            counter += 1
            self.get_logger().info(f'Counting... {counter}')
            
            # (3) 피드백 발행
            feedback_msg.current_number = counter
            goal_handle.publish_feedback(feedback_msg)
            
            # (4) 시간 지연 (실제 로봇 이동 시간 시뮬레이션)
            time.sleep(period)

        # 반복문이 정상적으로 끝났다면 성공 처리
        goal_handle.succeed()
        
        # 최종 결과 반환
        result.reached_number = counter
        self.get_logger().info(f'Goal succeeded. Result: {result.reached_number}')
        return result

def main(args=None):
    rclpy.init(args=args)
    node = CountUntilServer()
    
    # [심화] 액션 서버는 블로킹되는 작업(time.sleep 등)을 수행하므로
    # 멀티스레드 실행기를 사용하는 것이 안전하다.
    executor = MultiThreadedExecutor()
    rclpy.spin(node, executor=executor)
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()
