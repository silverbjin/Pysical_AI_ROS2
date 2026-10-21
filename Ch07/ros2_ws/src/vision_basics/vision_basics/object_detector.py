#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
# 수정됨: Point 대신 PointStamped 사용 (Header 포함)
from geometry_msgs.msg import PointStamped 
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np

class ObjectDetector(Node):
    def __init__(self):
        super().__init__('object_detector')

        # [QoS 설정] Gazebo 영상 데이터 손실 방지
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # 1. Subscriber: 카메라 영상 수신
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            qos_profile
        )

        # 2. Publisher: 디버깅용 이미지 & 물체 픽셀 좌표 송신
        self.img_pub = self.create_publisher(Image, '/camera/detection_result', 10)
        
        # 수정됨: PointStamped 타입으로 변경
        self.coord_pub = self.create_publisher(PointStamped, '/camera/target_pixel', 10)

        self.bridge = CvBridge()
        
        # Reject small noisy blobs; units are pixel squared (not metres).
        self.declare_parameter('min_contour_area', 500.0)
        self.min_contour_area = float(self.get_parameter('min_contour_area').value)
        if self.min_contour_area <= 0:
            raise ValueError('min_contour_area must be positive')

        # [색상 범위 설정] 'Red' Coke Can Detection
        self.lower_red1 = np.array([0, 100, 100])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([170, 100, 100])
        self.upper_red2 = np.array([180, 255, 255])

        self.get_logger().info('Object Detector Initialized: Looking for RED objects.')

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge Error: {e}')
            return

        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)

            if area >= self.min_contour_area:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # 시각화
                    cv2.drawContours(cv_image, [c], -1, (0, 255, 0), 2)
                    cv2.circle(cv_image, (cx, cy), 7, (255, 0, 0), -1)
                    cv2.putText(cv_image, f"({cx}, {cy})", (cx - 20, cy - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    
                    # 수정됨: PointStamped 객체 생성 및 데이터 할당
                    point_msg = PointStamped()
                    # 카메라 이미지 원본의 시간(Header)을 그대로 복사하여 동기화
                    point_msg.header = msg.header 
                    point_msg.point.x = float(cx)
                    point_msg.point.y = float(cy)
                    # Legacy PointStamped contract: x/y=pixels, z=area in pixel^2.
                    # This is NOT a 3D point; 7.5 must ignore z as depth.
                    point_msg.point.z = float(area) 
                    self.coord_pub.publish(point_msg)

        # No detection publishes NO target; downstream consumers MUST enforce TTL.
        # 결과 이미지 Publish
        try:
            detected_img_msg = self.bridge.cv2_to_imgmsg(cv_image, "bgr8")
            detected_img_msg.header = msg.header 
            self.img_pub.publish(detected_img_msg)
        except CvBridgeError as e:
            self.get_logger().error(f'CV Bridge Pub Error: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
