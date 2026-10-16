#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Point, PointStamped, TransformStamped
from sensor_msgs.msg import CameraInfo, Image
from cv_bridge import CvBridge
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
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

        # 1. TF Buffer & Listener 설정 (좌표 변환용 - 수신)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # [핵심 추가] 2. TF Broadcaster 설정 (타겟 프레임 발행용 - 송신)
        self.tf_broadcaster = TransformBroadcaster(self)

        # 내부 파라미터 및 변수
        self.fx = 0.0
        self.fy = 0.0
        self.cx = 0.0
        self.cy = 0.0
        self.camera_model_ready = False
        self.current_depth_image = None
        self.bridge = CvBridge()

        # Subscriber
        self.create_subscription(CameraInfo, '/camera/camera_info', self.info_callback, qos_profile)
        self.create_subscription(Image, '/camera/depth/image_raw', self.depth_callback, qos_profile)
        self.create_subscription(Point, '/camera/target_pixel', self.pixel_callback, 10)

        self.get_logger().info("Coordinate Transformer (TF Broadcaster Enabled) Initialized.")

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

        u = int(msg.x)
        v = int(msg.y)
        # z_depth = 0.5 
        z_depth = 0.5
        
        if self.current_depth_image is not None:
            h, w = self.current_depth_image.shape
            if 0 <= u < w and 0 <= v < h:
                d_val = self.current_depth_image[v, u]
                if not np.isnan(d_val) and d_val > 0.1:
                    z_depth = float(d_val)
        
        # 2D -> 3D 역투영 (카메라 렌즈 기준)
        x_c = (u - self.cx) * z_depth / self.fx
        y_c = (v - self.cy) * z_depth / self.fy
        z_c = z_depth

        # Camera Frame -> Robot Base Frame 변환
        try:
            point_camera = PointStamped()
            point_camera.header.frame_id = "camera_optical_frame"
            point_camera.header.stamp = self.get_clock().now().to_msg()
            point_camera.point.x = x_c
            point_camera.point.y = y_c
            point_camera.point.z = z_c

            transform = self.tf_buffer.lookup_transform(
                "base_link", 
                "camera_optical_frame",
                rclpy.time.Time(),
                rclpy.duration.Duration(seconds=1.0)
            )

            point_base = do_transform_point(point_camera, transform)

            # [핵심 추가] 변환된 좌표를 TF 트리 상의 새로운 프레임으로 등록
            self.broadcast_target_tf(point_base)

        except Exception as e:
            self.get_logger().warn(f"TF Transform failed: {e}")

    def broadcast_target_tf(self, point_stamped):
        """계산된 base_link 기준의 3D 좌표를 'target_object'라는 TF 프레임으로 방송"""
        t = TransformStamped()

        # 헤더 설정: 언제, 누구를 기준으로 만들어진 프레임인가?
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "base_link"
        
        # 생성할 새로운 자식 프레임의 이름
        t.child_frame_id = "target_object"

        # 위치 (Translation) 설정
        t.transform.translation.x = point_stamped.point.x
        t.transform.translation.y = point_stamped.point.y
        t.transform.translation.z = point_stamped.point.z

        # 자세 (Rotation/Quaternion) 설정
        # 현재는 비전에서 객체의 기울기를 알 수 없으므로 회전이 없는 상태(Identity)로 둡니다.
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0

        # TF 트리로 전송
        self.tf_broadcaster.sendTransform(t)
        
        self.get_logger().info(f"Published TF Frame [target_object] at ({t.transform.translation.x:.3f}, {t.transform.translation.y:.3f}, {t.transform.translation.z:.3f})")

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