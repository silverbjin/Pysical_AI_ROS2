#!/usr/bin/env python3
# my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import math

class TrotGaitPreview(Node):
    def __init__(self):
        super().__init__('trot_gait_preview')
        
        # 1. 4개 다리의 허벅지(Thigh) 관절 토픽 정의
        # 브리지 매핑 규칙에 따라 ROS 2 영역에서는 /0/이 없는 표준 주소를 사용합니다.
        self.topics = {
            'FL': '/model/my_quadruped/joint/fl_thigh_joint/cmd_pos',
            'RR': '/model/my_quadruped/joint/rr_thigh_joint/cmd_pos',
            'FR': '/model/my_quadruped/joint/fr_thigh_joint/cmd_pos',
            'RL': '/model/my_quadruped/joint/rl_thigh_joint/cmd_pos'
        }
        
        # 각 토픽에 대한 퍼블리셔 동적 생성 및 딕셔너리 저장
        self.pubs = {}
        for leg, topic in self.topics.items():
            self.pubs[leg] = self.create_publisher(Float64, topic, 10)
            
        # 2. 타이머 설정 (100Hz = 0.01초 간격 궤적 생성)
        self.timer_period = 0.01
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 3. 보행 패턴 생성기(Gait Pattern Generator) 파라미터 설정
        self.time = 0.0
        
        # [Method C 반영] 로봇이 서 있을 때의 실제 허벅지 중심 각도 (-0.6 rad)
        self.offset = -0.6        
        
        # 제자리 걸음의 안정성을 위해 진폭과 주파수를 조밀하게 세팅
        self.amplitude = 0.25      # 흔드는 범위 (+- 0.25 rad)
        self.frequency = 1.5       # 주파수 (1.5Hz = 1초에 1.5회 왕복하여 역동성 확보)
        
        self.get_logger().info("=== Trot Gait Preview Node Started ===")
        self.get_logger().info("Group A (FL, RR) and Group B (FR, RL) are synchronized with 180° phase shift.")

    def timer_callback(self):
        # 각속도 대입 각도 계산 (omega * t = 2 * pi * f * t)
        omega_t = 2.0 * math.pi * self.frequency * self.time
        
        # -----------------------------------------------------------------
        # [핵심] 위상차(Phase Shift) 알고리즘 적용
        # -----------------------------------------------------------------
        # Group A: 앞왼쪽(FL) + 뒤오른쪽(RR) -> 기준 위상 (0 rad)
        angle_group_a = self.offset + self.amplitude * math.sin(omega_t)
        
        # Group B: 앞오른쪽(FR) + 뒤왼쪽(RL) -> 180도 위상차 (+ math.pi)
        angle_group_b = self.offset + self.amplitude * math.sin(omega_t + math.pi)
        
        # 4개 다리에 메시지 실어서 발행 (토크 분산 및 동시성 확보)
        msg_a = Float64(data=angle_group_a)
        msg_b = Float64(data=angle_group_b)
        
        # Group A 전송
        self.pubs['FL'].publish(msg_a)
        self.pubs['RR'].publish(msg_a)
        
        # Group B 전송
        self.pubs['FR'].publish(msg_b)
        self.pubs['RL'].publish(msg_b)
        
        # 4. 시간 누적
        self.time += self.timer_period

def main(args=None):
    rclpy.init(args=args)
    node = TrotGaitPreview()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node interrupted by user.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()