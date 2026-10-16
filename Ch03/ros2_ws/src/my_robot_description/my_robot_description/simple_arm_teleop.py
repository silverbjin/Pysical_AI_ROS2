#!/usr/bin/env python3
import sys
import termios
import tty
import select
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

# =============================================================================
# 설정: 제어할 키 매핑 및 제한 사항
# =============================================================================
msg = """
--------------------------------------------------
My Robot Arm Teleoperation
--------------------------------------------------
Key Map:
   W / S : Joint 1 (Shoulder) Increase / Decrease
   A / D : Joint 2 (Elbow)    Increase / Decrease
   
   Q     : Quit
--------------------------------------------------
"""

# 각도 제한 (Radian)
JOINT1_LIMIT = {'min': -1.57, 'max': 1.57} # -90도 ~ 90도
JOINT2_LIMIT = {'min': -1.57, 'max': 1.57}

# 한 번 누를 때마다 변하는 각도 크기 (Step size)
STEP_SIZE = 0.05  # 약 2.8도

class SimpleArmTeleop(Node):
    def __init__(self):
        super().__init__('simple_arm_teleop')
        
        # 1. Publisher 생성: Gazebo Bridge와 연결된 토픽으로 Float64 메시지 전송
        self.pub_j1 = self.create_publisher(
            Float64, 
            '/joint1/cmd_pos', 
            10)
        self.pub_j2 = self.create_publisher(
            Float64, 
            '/joint2/cmd_pos', 
            10)

        # 2. 현재 각도 상태 저장 (초기값 0.0)
        self.joint1_pos = 0.0
        self.joint2_pos = 0.0

        # 3. 터미널 설정 저장 (종료 시 복구하기 위함)
        self.settings = termios.tcgetattr(sys.stdin)

    def get_key(self):
        """
        터미널에서 키 입력 하나를 받아오는 함수 (Blocking 없이 처리)
        핵심은 '엔터키 없이 바로 입력받기'를 구현한 리눅스 시스템 프로그래밍 영역입니다.
        """
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def publish_commands(self):
        """현재 설정된 각도를 토픽으로 발행"""
        msg_j1 = Float64()
        msg_j1.data = self.joint1_pos
        self.pub_j1.publish(msg_j1)

        msg_j2 = Float64()
        msg_j2.data = self.joint2_pos
        self.pub_j2.publish(msg_j2)

    def constrain(self, val, min_val, max_val):
        """각도 제한 함수 (Hard Limit)"""
        return max(min(val, max_val), min_val)

def main(args=None):
    rclpy.init(args=args)
    node = SimpleArmTeleop()

    print(msg)

    try:
        while rclpy.ok():
            # 1. 키 입력 받기
            key = node.get_key()

            # 2. 키에 따른 각도 변화 로직
            if key == 'w':
                node.joint1_pos += STEP_SIZE
                print(f"Joint 1 Up: {node.joint1_pos:.2f}")
            elif key == 's':
                node.joint1_pos -= STEP_SIZE
                print(f"Joint 1 Down: {node.joint1_pos:.2f}")
            elif key == 'a':
                node.joint2_pos += STEP_SIZE
                print(f"Joint 2 Up: {node.joint2_pos:.2f}")
            elif key == 'd':
                node.joint2_pos -= STEP_SIZE
                print(f"Joint 2 Down: {node.joint2_pos:.2f}")
            elif key == 'q': # 종료
                print("Quitting...")
                break
            elif key == '\x03': # Ctrl+C 처리
                break

            # 3. 각도 제한 적용 (Limit): 로봇이 360도 회전해서 꼬이는 것을 방지
            node.joint1_pos = node.constrain(node.joint1_pos, JOINT1_LIMIT['min'], JOINT1_LIMIT['max'])
            node.joint2_pos = node.constrain(node.joint2_pos, JOINT2_LIMIT['min'], JOINT2_LIMIT['max'])

            # 4. 명령 발행
            node.publish_commands()

    except Exception as e:
        print(e)

    finally:
        # 터미널 설정 복구 및 종료
        node.destroy_node()
        rclpy.shutdown()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, node.settings)

if __name__ == '__main__':
    main()
