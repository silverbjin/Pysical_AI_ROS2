#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint

class GripperController(Node):
    def __init__(self):
        super().__init__('gripper_controller')
        
        # 1. Action Client 생성
        # controller_manager에 정의된 그리퍼 컨트롤러 이름 확인 필수!
        # 보통 'gripper_controller/follow_joint_trajectory' 형태임
        self._action_client = ActionClient(
            self, 
            FollowJointTrajectory, 
            '/gripper_group_controller/follow_joint_trajectory'
        )

        self.get_logger().info("Gripper Action Client Waiting...")
        self._action_client.wait_for_server()
        self.get_logger().info("Gripper Server Connected!")

    def move_gripper(self, position):
        """
        그리퍼를 특정 위치(너비)로 이동시키는 함수
        """
        goal_msg = FollowJointTrajectory.Goal()
        
        # 2. 조인트 이름 설정 (ros2_controllers.yaml과 완벽히 일치해야 함)
        # ⬅️ [수정] 단일 조인트에서 2개의 핑거 조인트 배열로 변경
        goal_msg.trajectory.joint_names = ['joint_finger1', 'joint_finger2']

        # 3. 궤적 포인트 생성
        point = JointTrajectoryPoint()
        
        # ⬅️ [수정] 조인트가 2개이므로, 목표 위치값도 2개를 배열로 전달해야 합니다.
        # (주의: URDF 모델의 회전/이동 축 설계에 따라 한쪽을 -position으로 줘야 할 수도 있습니다.)
        point.positions = [position, position]
        
        point.time_from_start.sec = 1 
        point.time_from_start.nanosec = 0
        
        goal_msg.trajectory.points = [point]

        # 4. 액션 전송
        self.get_logger().info(f"Sending Gripper Goal: {position}")
        self._send_goal_future = self._action_client.send_goal_async(goal_msg)
        self._send_goal_future.add_done_callback(self.goal_response_callback)
    
    # def move_gripper(self, position):
    #     """
    #     그리퍼를 특정 위치(너비)로 이동시키는 함수
    #     :param position: 0.0 (닫힘) ~ Max (열림). 단위: 라디안 또는 미터
    #     """
    #     goal_msg = FollowJointTrajectory.Goal()
        
    #     # 2. 조인트 이름 설정 (URDF와 일치해야 함)
    #     # 2-Finger 그리퍼는 보통 두 개의 조인트가 있지만, 
    #     # Mimic Joint로 설정되어 하나만 제어하면 되는 경우가 많다.
    #     goal_msg.trajectory.joint_names = ['gripper_joint'] 

    #     # 3. 궤적 포인트 생성
    #     point = JointTrajectoryPoint()
    #     point.positions = [position]
    #     point.time_from_start.sec = 1 # 1초 동안 이동
    #     point.time_from_start.nanosec = 0
        
    #     goal_msg.trajectory.points = [point]

    #     # 4. 액션 전송
    #     self.get_logger().info(f"Sending Gripper Goal: {position}")
    #     self._send_goal_future = self._action_client.send_goal_async(goal_msg)
    #     self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Gripper Goal Rejected')
            return
        self.get_logger().info('Gripper Goal Accepted')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        self.get_logger().info(f'Gripper Action Finished: {future.result().result}')

    # [편의 함수]
    # def open(self):
    #     self.move_gripper(0.04) # 8cm (최대 개방) 0.025 성공
    # def close(self):
    #     self.move_gripper(0.01) # 0cm (완전 닫힘) 0.01 성공
    # [방향 수정]
    def open(self):
        self.move_gripper(0.005) # 0cm (완전 열림) 0.01 성공
        
    def close(self):
        self.move_gripper(0.02) # 0.1cm (완전 닫힘) 0.025 성공


def main(args=None):
    rclpy.init(args=args)
    gripper = GripperController()

    # 테스트 시나리오
    import time
    time.sleep(1)    
    gripper.open()   # 열기
    time.sleep(3)
    gripper.get_logger().info('opening gripper...')
    gripper.close()  # 닫기
    gripper.get_logger().info('closing gripper...')
    
    try:
        rclpy.spin(gripper)
    except KeyboardInterrupt:
        pass
    finally:
        gripper.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

