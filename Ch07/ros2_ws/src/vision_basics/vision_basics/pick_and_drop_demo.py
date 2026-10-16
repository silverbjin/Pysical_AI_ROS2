#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
import threading
import time

class PickAndDropDemo(Node):
    def __init__(self):
        super().__init__('pick_and_drop_demo')
        
        # 1. Arm 및 Gripper 액션 클라이언트 생성
        self.arm_client = ActionClient(self, FollowJointTrajectory, '/arm_group_controller/follow_joint_trajectory')
        self.gripper_client = ActionClient(self, FollowJointTrajectory, '/gripper_group_controller/follow_joint_trajectory')
        
        self.get_logger().info("액션 서버 연결 대기 중...")
        self.arm_client.wait_for_server()
        self.gripper_client.wait_for_server()
        self.get_logger().info("모든 서버 연결 완료! 데모 시퀀스를 시작합니다.")

        # 2. 메인 스레드의 rclpy.spin() 블로킹을 피하기 위해 별도 스레드에서 시나리오 실행
        self.demo_thread = threading.Thread(target=self.run_sequence)
        self.demo_thread.start()

    def move_arm(self, positions, duration_sec):
        """로봇 팔 제어 헬퍼 함수"""
        goal_msg = FollowJointTrajectory.Goal()
        # [주의] URDF의 조인트 이름과 완벽히 일치해야 합니다.
        goal_msg.trajectory.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint_wrist']
        
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start.sec = duration_sec
        goal_msg.trajectory.points = [point]
        
        self.get_logger().info(f"팔 이동 명령 전송: {positions}")
        self.arm_client.send_goal_async(goal_msg)

    def move_gripper(self, pos, duration_sec):
        """그리퍼 제어 헬퍼 함수"""
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = ['joint_finger1', 'joint_finger2']
        
        point = JointTrajectoryPoint()
        point.positions = [pos, pos]
        point.time_from_start.sec = duration_sec
        point.time_from_start.nanosec = 0
        goal_msg.trajectory.points = [point]
        
        self.get_logger().info(f"그리퍼 작동 명령 전송: {pos}")
        self.gripper_client.send_goal_async(goal_msg)

    def run_sequence(self):
        """시간 흐름에 따른 데모 절차 (절차적 프로그래밍 스타일)"""
        # [수치 주의] 아래 각도(Radian)는 로봇의 실제 Kinematics에 맞게 수정해야 합니다.
        # 예시: [Base, Shoulder, Elbow, Wrist1, Wrist2]
        
        # 1. 초기 위치 (Home) & 그리퍼 열기
        self.move_arm([0.0, 0.807, 1.732, -1.5707, 0.0], 2)
        self.move_gripper(0.005, 1) # 4cm 열기        
        time.sleep(8) # 동작 완료 대기
        
        # 2. 물체 위로 팔 내리기 (Pre-Grasp)
        self.move_arm([0.0, 0.807, 1.732, -1.5707, 0.0], 2)        
        time.sleep(2)
        
        # 3. 그리퍼 닫기 (물체 파지)
        # 0.0이 완전 닫힘이라면, 5cm 큐브 파지를 위해 약간의 여유를 줍니다.
        self.move_gripper(0.025, 1)         
        time.sleep(2)
        
        # 4. 팔 위로 들어올리기 (Lift)
        self.move_arm([0.0, 0, 1.732, -1.5707, 0.0], 2)
        time.sleep(5)
        
        # 5. 그리퍼 열기 (Drop)
        self.move_gripper(0.005, 1) # 4cm 열기 -> 8
        self.get_logger().info("데모 시퀀스 완료!")

def main(args=None):
    rclpy.init(args=args)
    node = PickAndDropDemo()
    
    try:
        rclpy.spin(node) # 노드 통신 유지
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()