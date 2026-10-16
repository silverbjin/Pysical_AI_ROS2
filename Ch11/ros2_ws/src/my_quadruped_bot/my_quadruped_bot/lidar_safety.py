#!/usr/bin/env python3
"""
장치: Physical AI 사족 보행 로봇 가이드
파일명: lidar_safety.py
내용: ROI(관심 영역) 필터링 기반 전방 장애물 감지 및 안전 제동 판단 노드
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import LaserScan
import math

class LidarSafety(Node):
    def __init__(self):
        super().__init__('lidar_safety')

        # 1. QoS 설정: 실시간 장애물 대응을 위해 BEST_EFFORT 및 버퍼 최소화
        qos_policy = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5
        )

        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',  # ros_gz_bridge에서 매핑한 표준 토픽명 구독
            self.lidar_callback,
            qos_policy
        )
        
        # 안전 기준 파라미터 설정 (1.5m)
        self.safe_distance = 1.5
        self.get_logger().info("LiDAR 비상 안전 제동 노드가 가동되었습니다. 전방 30도 섹터를 감시합니다.")

    def lidar_callback(self, msg: LaserScan):
        # 1. 센서 메타데이터 및 배열 추출
        ranges = msg.ranges
        angle_min = msg.angle_min
        angle_inc = msg.angle_increment
        
        valid_distances = []

        # 2. [구조 개선] 인덱스 슬라이싱 대신 360도 전수 조사를 통한 각도 매칭 마스킹
        # 센서의 시작 각도와 인덱스 구조가 바뀌어도 에러 없이 항상 정확한 정면 ROI를 확보함
        for i, dist in enumerate(ranges):
            # 현재 데이터의 물리적 실제 각도 역산 [rad]
            current_angle = angle_min + (i * angle_inc)
            
            # [ROI 필터링] 로봇 정면(0도) 기준 좌우 30도 범위 이내의 데이터만 추출
            if abs(current_angle) <= math.radians(30):
                
                # [예외 처리] 무한대(inf), 잘못된 음수 데이터 제거
                if math.isinf(dist) or math.isnan(dist):
                    continue
                    
                # [노이즈 제거] 센서의 물리적 측정 최소 반경(range_min)보다 작은 값은 오차이므로 제외
                if dist < msg.range_min:
                    continue
                    
                valid_distances.append(dist)

        # 3. 전방 섹터 내 유효 거리가 없을 경우 안전 상태로 판단
        if not valid_distances:
            return

        # 4. 최단거리 산출 및 비상 제동 판단
        min_dist = min(valid_distances)
        
        if min_dist < self.safe_distance:
            # 실무 관점의 경고 전송 (가독성을 위한 이모지 및 변수 강조)
            self.get_logger().warn(
                f"🚨 [충돌 위험] 전방 장애물 감지! 거리: {min_dist:.2f}m (안전 반경: {self.safe_distance}m)"
            )
            # [심화 과제 확장] 추후 이 위치에 cmd_vel 발행 코드를 연동하여 AEB(자동 긴급 제동) 완성
        else:
            self.get_logger().debug(f"전방 이상 없음. 최단 장애물: {min_dist:.2f}m")

def main(args=None):
    rclpy.init(args=args)
    node = LidarSafety()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()