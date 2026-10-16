#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
# [필수 임포트] 시각화 마커 메시지 타입
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Pose, Vector3
from std_msgs.msg import ColorRGBA

class MarkerObjectManager(Node):
    def __init__(self):
        super().__init__('marker_object_manager')

        # 1. RViz2 렌더링을 위한 전용 마커 퍼블리셔 선언
        self.marker_pub = self.create_publisher(Marker, '/robot/target_marker', 10)

        # 0.1초(10Hz)마다 마커를 발행하여 비전 좌표 추종성을 높임
        self.timer = self.create_timer(0.1, self.publish_coke_can_marker)

        self.get_logger().info("Lightweight RViz Marker Manager Initialized.")

    def publish_coke_can_marker(self):
        marker = Marker()
        
        # [핵심] coord_transformer.py가 발행하는 dynamic TF 프레임을 기준축으로 지정
        # 이 설정 덕분에 비전이 타겟을 놓치거나 움직이면 캔 형상도 실시간으로 따라 움직입니다.
        marker.header.frame_id = "target_object"
        marker.header.stamp = self.get_clock().now().to_msg()
        
        # 마커 식별을 위한 네임스페이스와 고유 ID
        marker.ns = "visual_targets"
        marker.id = 100
        
        # 마커 형태를 원기둥(CYLINDER)으로 지정
        marker.type = Marker.CYLINDER
        marker.action = Marker.ADD

        # 2. 코카콜라 캔 규격 매핑 (★교재 집필 팁)
        # 중요: URDF와 달리 RViz Marker의 CYLINDER 스케일은 [X=지름, Y=지름, Z=높이]를 뜻합니다.
        # 코카콜라 캔 표준 규격: 지름 66mm (0.066m), 높이 120mm (0.12m)
        marker.scale.x = 0.066  # X 지름
        marker.scale.y = 0.066  # Y 지름
        marker.scale.z = 0.12   # Z 높이

        # 3. 마커의 로컬 자세(Pose) 설정
        # TF 좌표축 정중앙에 캔의 중심이 매핑되므로, 
        # 캔 바닥이 타겟 포인트(TF 원점)에 딱 맞닿게 연출하려면 높이의 절반(0.06m)만큼 Z축으로 올립니다.
        marker.pose.position.x = 0.0
        marker.pose.position.y = 0.0
        marker.pose.position.z = 0.06
        
        marker.pose.orientation.x = 0.0
        marker.pose.orientation.y = 0.0
        marker.pose.orientation.z = 0.0
        marker.pose.orientation.w = 1.0

        # 4. 색상 설정 (코카콜라 시그니처 레드 연출)
        # RGBA 구조이며 값의 범위는 0.0 ~ 1.0 입니다.
        marker.color.r = 0.9    # 강렬한 빨간색
        marker.color.g = 0.0
        marker.color.b = 0.0
        marker.color.a = 0.95   # 약간의 투명감을 주어 내부 TF 축이 살짝 비치도록 연출 (디버깅 용이)

        # 마커 유효 수명 (0.2초 동안 새 마커가 오지 않으면 자동 삭제하여 고스트 현상 방지)
        marker.lifetime = rclpy.duration.Duration(seconds=0.2).to_msg()
        
        
        
        # [추가 연출] 글자 마커 (TEXT_VIEW_FACING은 카메라가 회전해도 글자가 항상 정면을 바라봄)
        text_marker = Marker()
        text_marker.header = marker.header
        text_marker.ns = "visual_labels"
        text_marker.id = 101 # ID가 달라야 원기둥을 덮어쓰지 않고 동시에 뜹니다.
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD

        # 원기둥 캔 윗면(높이 12cm)보다 살짝 위(17cm 지점)에 글자가 뜨도록 설정
        text_marker.pose.position.z = 0.17 
        text_marker.scale.z = 0.1 # 글자 크기 (3cm)

        # 글자 색상 (선명한 흰색)
        text_marker.color.r = 2.0; text_marker.color.g = 2.0; text_marker.color.b = 2.0; text_marker.color.a = 1.0

        # 표시할 텍스트 내용 문자열 지정
        text_marker.text = "TARGET:COKE CAN"
        text_marker.lifetime = marker.lifetime

        # 글자 마커 추가 발행
        self.marker_pub.publish(text_marker)
        

        # 최종 RViz로 송출
        self.marker_pub.publish(marker)
        


def main(args=None):
    rclpy.init(args=args)
    node = MarkerObjectManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()