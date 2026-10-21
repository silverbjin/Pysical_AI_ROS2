#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np

class VisionProcessor(Node):
    def __init__(self):
        super().__init__('vision_processor')

        self.declare_parameter('show_gui', False)
        self.show_gui = bool(self.get_parameter('show_gui').value)
        # 1. QoS 설정 (Gazebo와의 호환성 필수)
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # 2. Subscriber: 원본 이미지 수신
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.listener_callback,
            qos_profile
        )

        # 3. Publisher: 처리된 이미지(Edge) 송출
        # 처리된 이미지는 디버깅을 위해 'Reliable'로 보내기도 하지만,
        # 여기서는 원본과 동일하게 맞춘다.
        self.publisher_ = self.create_publisher(Image, '/camera/processed_image', 10)

        # 4. Bridge 객체 생성
        self.bridge = CvBridge()
        
        self.get_logger().info('Vision Processor 노드가 시작되었습니다.')

    def listener_callback(self, msg):
        try:
            # [Step 1] ROS Image -> OpenCV Image 변환
            # 'bgr8': Blue, Green, Red 순서의 8비트 컬러 이미지
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge 변환 오류: {e}')
            return

        # [Step 2] 이미지 처리 (Computer Vision Algorithm)
        # 여기서는 예시로 Canny Edge Detection(윤곽선 검출)을 수행한다.
        # 컬러 이미지를 흑백으로 변환 -> 가우시안 블러 -> Canny 알고리즘 적용
        gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
        edge_image = cv2.Canny(blurred_image, 50, 150)

        # GUI is optional: ROS image publishing must work headlessly (WSL/SSH).
        if self.show_gui:
            try:
                cv2.imshow("Original View", cv_image)
                cv2.imshow("Edge Detection", edge_image)
                cv2.waitKey(1)
            except cv2.error as exc:
                self.get_logger().warning(f'Disabling GUI after OpenCV error: {exc}')
                self.show_gui = False

        # [Step 4] OpenCV Image -> ROS Image 역변환 및 송출
        try:
            # 흑백 이미지(mono8)로 변환하여 송출
            processed_msg = self.bridge.cv2_to_imgmsg(edge_image, encoding="mono8")
            # 헤더 정보 복사 (타임스탬프 동기화 중요)
            processed_msg.header = msg.header 
            
            self.publisher_.publish(processed_msg)
            
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge 역변환 오류: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = VisionProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 종료 시 OpenCV 창 모두 닫기
        if node.show_gui:
            cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
