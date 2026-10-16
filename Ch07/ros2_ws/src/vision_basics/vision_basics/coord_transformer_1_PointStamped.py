#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Point, PointStamped
from sensor_msgs.msg import CameraInfo, Image
from cv_bridge import CvBridge
from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_point
import numpy as np

class CoordTransformer(Node):
    def __init__(self):
        super().__init__('coord_transformer')

        # [QoS 설정]
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # 1. TF Buffer & Listener 설정 (좌표 변환의 핵심)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 2. 내부 파라미터(Intrinsics) 수신용 변수
        self.fx = 0.0
        self.fy = 0.0
        self.cx = 0.0
        self.cy = 0.0
        self.camera_model_ready = False

        # 3. Depth 이미지 저장용 변수
        self.current_depth_image = None
        self.bridge = CvBridge()

        # 4. Subscriber 정의
        self.create_subscription(CameraInfo, '/camera/camera_info', self.info_callback, qos_profile)
        self.create_subscription(Image, '/camera/depth/image_raw', self.depth_callback, qos_profile)
        self.create_subscription(Point, '/camera/target_pixel', self.pixel_callback, 10)

        # 5. Publisher 정의 (최종 3D 좌표)
        # self.target_pub = self.create_publisher(Point, '/robot/target_position', 10)
        self.target_pub = self.create_publisher(PointStamped, '/robot/target_position', 10)
        

        self.get_logger().info("Coordinate Transformer Initialized.")

    def info_callback(self, msg):
        if not self.camera_model_ready:
            # Pinhole Camera Matrix K = [fx, 0, cx; 0, fy, cy; 0, 0, 1]
            self.fx = msg.k[0]
            self.cx = msg.k[2]
            self.fy = msg.k[4]
            self.cy = msg.k[5]
            self.camera_model_ready = True
            self.get_logger().info(f"Camera Model Loaded: fx={self.fx}, fy={self.fy}")

    def depth_callback(self, msg):
        # Depth 이미지는 32bit float (32FC1) 형식이 일반적 (단위: meter)
        try:
            self.current_depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.get_logger().error(f"Depth convert error: {e}")

    def pixel_callback(self, msg):
        if not self.camera_model_ready:
            self.get_logger().warn("Waiting for camera info...")
            return

        u = int(msg.x)
        v = int(msg.y)

        # [Step 1] 깊이(Z) 값 획득
        z_depth = 0.5 # Default (50cm) - Depth 센서가 없을 때를 대비한 안전장치
        
        if self.current_depth_image is not None:
            # 이미지 범위를 벗어나는지 확인
            h, w = self.current_depth_image.shape
            if 0 <= u < w and 0 <= v < h:
                d_val = self.current_depth_image[v, u]
                # 유효한 깊이 값인지 확인 (NaN 또는 0이 아닐 경우)
                if not np.isnan(d_val) and d_val > 0.1:
                    z_depth = float(d_val)
        
        # [Step 2] 2D Pixel (u,v) -> 3D Camera Coordinate (Xc, Yc, Zc)
        # 역투영 공식 (Back-Projection)
        x_c = (u - self.cx) * z_depth / self.fx
        y_c = (v - self.cy) * z_depth / self.fy
        z_c = z_depth

        self.get_logger().info(f"Camera Coord: ({x_c:.3f}, {y_c:.3f}, {z_c:.3f})")

        # [Step 3] Camera Frame -> Robot Base Frame 변환
        try:
            # 변환할 포인트 객체 생성 (Stamped 필수)
            point_camera = PointStamped()
            point_camera.header.frame_id = "camera_optical_frame" # 중요! 광학 프레임 기준
            point_camera.header.stamp = self.get_clock().now().to_msg()
            point_camera.point.x = x_c
            point_camera.point.y = y_c
            point_camera.point.z = z_c

            # TF Buffer를 이용해 변환 조회 ('base_link' 기준으로 변환해라)
            # 타임아웃 1.0초 설정 (TF 트리가 업데이트될 시간을 줌)
            transform = self.tf_buffer.lookup_transform(
                "base_link", 
                "camera_optical_frame",
                rclpy.time.Time(),
                rclpy.duration.Duration(seconds=1.0)
            )

            # 실제 좌표 변환 수행
            point_base = do_transform_point(point_camera, transform)

            # [Step 4] 결과 발행
            # self.target_pub.publish(point_base.point)
            self.target_pub.publish(point_base)  # point_base 객체를 .point를 떼어내지 않고 통째로 발행
            
            self.get_logger().info(
                f"TRANSFORMED -> Base Coord: X={point_base.point.x:.3f}, "
                f"Y={point_base.point.y:.3f}, Z={point_base.point.z:.3f}"
            )

        except Exception as e:
            self.get_logger().warn(f"TF Transform failed: {e}")

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
