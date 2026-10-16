#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Point, PointStamped
from sensor_msgs.msg import CameraInfo, Image
# [필수 추가] 시각화 마커 메시지 임포트
from visualization_msgs.msg import Marker 
from cv_bridge import CvBridge
from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_point
import numpy as np

class CoordTransformer(Node):
    def __init__(self):
        super().__init__('coord_transformer')

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.camera_model_ready = False
        self.current_depth_image = None
        self.bridge = CvBridge()

        # Subscriber
        self.create_subscription(CameraInfo, '/camera/camera_info', self.info_callback, qos_profile)
        self.create_subscription(Image, '/camera/depth/image_raw', self.depth_callback, qos_profile)
        self.create_subscription(Point, '/camera/target_pixel', self.pixel_callback, 10)

        # 1. Marker Publisher 정의 (RViz 모니터링 전용 단일 토픽)
        self.marker_pub = self.create_publisher(Marker, '/robot/target_marker', 10)

        self.get_logger().info("Coordinate Transformer with Marker Initialized.")

    def info_callback(self, msg):
        if not self.camera_model_ready:
            self.fx = msg.k[0]
            self.cx = msg.k[2]
            self.fy = msg.k[4]
            self.cy = msg.k[5]
            self.camera_model_ready = True

    def depth_callback(self, msg):
        try:
            self.current_depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"Depth convert error: {e}")

    def pixel_callback(self, msg):
        if not self.camera_model_ready:
            return

        u, v = int(msg.x), int(msg.y)
        z_depth = 0.5 
        
        if self.current_depth_image is not None:
            h, w = self.current_depth_image.shape
            if 0 <= u < w and 0 <= v < h:
                d_val = self.current_depth_image[v, u]
                if not np.isnan(d_val) and d_val > 0.1:
                    z_depth = float(d_val)
        
        # 2D -> 3D 역투영
        x_c = (u - self.cx) * z_depth / self.fx
        y_c = (v - self.cy) * z_depth / self.fy
        z_c = z_depth

        # Camera -> Base Frame 변환
        try:
            point_camera = PointStamped()
            point_camera.header.frame_id = "camera_optical_frame"
            point_camera.header.stamp = self.get_clock().now().to_msg()
            point_camera.point.x = x_c
            point_camera.point.y = y_c
            point_camera.point.z = z_c

            transform = self.tf_buffer.lookup_transform(
                "base_link", "camera_optical_frame", rclpy.time.Time(), rclpy.duration.Duration(seconds=1.0)
            )
            point_base = do_transform_point(point_camera, transform)

            # 2. RViz 시각화를 위한 마커 생성 및 발행 함수 호출
            self.publish_target_marker(point_base)

        except Exception as e:
            self.get_logger().warn(f"TF Transform failed: {e}")

    def publish_target_marker(self, point_stamped):
        """계산된 3D 좌표를 바탕으로 입체 구체(Sphere) 마커를 발행하는 함수"""
        marker = Marker()
        # 헤더 정보 동기화 (base_link 기준 타임스탬프 설정)
        marker.header = point_stamped.header
        
        # 네임스페이스와 ID는 마커의 고유 이름표입니다 (여러 마커 관리 시 유용)
        marker.ns = "gripping_target"
        marker.id = 0
        
        # 마커 형태 정의 (SPHERE, ARROW, CUBE, TEXT_VIEW_FACING 등이 가능)
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD  # 생성/갱신 명령
        
        # 3D 위치 설정 (do_transform_point로 변환된 좌표계 그대로 대입)
        marker.pose.position = point_stamped.point
        marker.pose.orientation.w = 1.0  # 회전이 없는 구체 형태이므로 쿼터니언 기본값
        
        # 마커의 크기 (단위: 미터) -> 직경 5cm 크기의 구체
        marker.scale.x = 0.05
        marker.scale.y = 0.05
        marker.scale.z = 0.05
        
        # 마커의 색상 설정 (RGBA) -> 강렬한 반투명 빨간색
        marker.color.r = 1.0
        marker.color.g = 0.0
        marker.color.b = 0.0
        marker.color.a = 0.8  # 불투명도 (0.0 ~ 1.0)
        
        # 잔상 유지 시간 설정 (0.5초 동안 새 데이터가 안 오면 자동 소멸하여 유령 마커 방지)
        marker.lifetime = rclpy.duration.Duration(seconds=0.5).to_msg()
        
        # 최종 발행
        self.marker_pub.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = CoordTransformer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()