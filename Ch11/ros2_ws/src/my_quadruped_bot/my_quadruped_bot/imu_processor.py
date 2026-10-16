#!/usr/bin/env python3
"""
장치: Physical AI 사족 보행 로봇 가이드
파일명: imu_processor.py
내용: 상보 필터 기반 IMU 데이터 정제 및 오일러 각도(RPY) 추출 노드
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray
import math

class ImuProcessor(Node):
    def __init__(self):
        super().__init__('imu_processor')
        
        # 1. QoS 설정: 센서 데이터 유실 대응 및 실시간성 확보를 위해 BEST_EFFORT 적용
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        # 2. Subscriber: 무한 루프 방지를 위해 원시 데이터 토픽(/imu/data_raw) 분리 구독
        self.create_subscription(
            Imu,
            '/imu/data_raw',  
            self.imu_callback,
            qos_profile
        )

        # 3. Publisher: 필터링된 Roll, Pitch, Yaw 데이터 발행
        self.rpy_pub = self.create_publisher(Float32MultiArray, '/imu/rpy_filtered', 10)

        # 4. 필터 상태 변수 및 파라미터 초기화
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.last_time = None  # 첫 루프에서 타임스탬프를 안전하게 동기화하기 위해 None으로 설정

        # 상보 필터 계수 (자이로스코프 신뢰도 98%, 가속도계 신뢰도 2%)
        self.alpha = 0.98 

        self.get_logger().info("IMU Processor Node 가 성공적으로 시작되었습니다.")

    def imu_callback(self, msg):
        # 현재 메시지의 헤더 타임스탬프 또는 시스템 시계 기반으로 시간 추출
        current_time = self.get_clock().now().nanoseconds / 1e9
        
        # [엣지 케이스 처리] 첫 번째 루프인 경우 dt 계산을 건너뛰고 초기 자세만 할당
        if self.last_time is None:
            self.last_time = current_time
            self.roll = math.atan2(msg.linear_acceleration.y, msg.linear_acceleration.z)
            self.pitch = math.atan2(-msg.linear_acceleration.x, math.sqrt(msg.linear_acceleration.y**2 + msg.linear_acceleration.z**2))
            return

        # 시간 변위(dt) 계산
        dt = current_time - self.last_time
        
        # [엣지 케이스 처리] 시뮬레이션 타임스탬프 역전이나 정지 상태(dt <= 0) 발생 시 예외 처리
        if dt <= 0.0:
            return
            
        self.last_time = current_time

        # ---------------------------------------------------------
        # 단계 1: 가속도계 데이터로 Roll, Pitch 계산 (고주파 노이즈에 취약)
        # ---------------------------------------------------------
        ax = msg.linear_acceleration.x
        ay = msg.linear_acceleration.y
        az = msg.linear_acceleration.z

        # 중력 벡터 기반 오일러 각도 산출 (보행 충격 시 데이터가 크게 흔들림)
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.sqrt(ay*ay + az*az))

        # ---------------------------------------------------------
        # 단계 2: 자이로스코프 데이터 추출 (누적 드리프트에 취약)
        # ---------------------------------------------------------
        gx = msg.angular_velocity.x
        gy = msg.angular_velocity.y
        gz = msg.angular_velocity.z

        # ---------------------------------------------------------
        # 단계 3: 상보 필터(Complementary Filter) 및 각도 정규화 적용
        # ---------------------------------------------------------
        # 수식 동기화: theta_new = alpha * (theta_old + omega * dt) + (1 - alpha) * theta_acc
        self.roll = self.alpha * (self.roll + gx * dt) + (1.0 - self.alpha) * roll_acc
        self.pitch = self.alpha * (self.pitch + gy * dt) + (1.0 - self.alpha) * pitch_acc
        
        # Yaw 축은 가속도계(중력)로 보정이 불가능하므로 단순 적분 처리
        self.yaw = self.yaw + gz * dt  

        # [수정 보완] Yaw 각도가 무한히 증가하는 것을 방지하기 위해 [-pi, pi] 범위로 정규화
        self.yaw = math.atan2(math.sin(self.yaw), math.cos(self.yaw))

        # ---------------------------------------------------------
        # 단계 4: 데이터 정제 및 발행
        # ---------------------------------------------------------
        rpy_msg = Float32MultiArray()
        rpy_msg.data = [self.roll, self.pitch, self.yaw]
        self.rpy_pub.publish(rpy_msg)

def main(args=None):
    rclpy.init(args=args)
    node = ImuProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()