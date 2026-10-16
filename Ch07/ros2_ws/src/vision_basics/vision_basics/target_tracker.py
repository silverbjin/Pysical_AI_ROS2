#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped, TransformStamped  # TransformStamped 추가
from tf2_ros import TransformBroadcaster                       # TF 브로드캐스터 추가
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

class TargetTracker3D(Node):
    def __init__(self):
        super().__init__('target_tracker_3d')
        self.bridge = CvBridge()
        self.latest_depth_msg = None

        # 1. TF 브로드캐스터 초기화
        self.tf_broadcaster = TransformBroadcaster(self)

        # [QoS 설정] 영상 데이터용
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5
        )

        # 2. Subscriber 설정
        self.depth_sub = self.create_subscription(
            Image,
            '/camera/depth/image_raw',
            self.depth_callback,
            qos_profile
        )

        self.pixel_sub = self.create_subscription(
            PointStamped,
            '/camera/target_pixel',
            self.pixel_callback,
            10
        )

        # 카메라 내부 파라미터 (Intrinsic Matrix)
        self.fx = 554.25
        self.fy = 554.25
        self.cx = 320.0
        self.cy = 240.0

        self.get_logger().info('Target Tracker 3D Initialized with TF Broadcaster.')

    def depth_callback(self, msg):
        self.latest_depth_msg = msg

    def pixel_callback(self, msg):
        # 2D 객체 인식 실패 시 예외 처리
        if msg.point.x == -1 or msg.point.y == -1:
            return

        target_u = int(msg.point.x)
        target_v = int(msg.point.y)

        if self.latest_depth_msg is None:
            return

        try:
            # ROS Depth Image -> OpenCV 변환
            depth_image = self.bridge.imgmsg_to_cv2(self.latest_depth_msg, desired_encoding="passthrough")
            h, w = depth_image.shape[:2]

            if 0 <= target_u < w and 0 <= target_v < h:
                depth = depth_image[target_v, target_u]

                # 시뮬레이터 환경 및 하드웨어 인코딩에 따른 미터 단위 예외 처리
                if depth_image.dtype == np.uint16:
                    depth = float(depth) / 1000.0

                if np.isnan(depth) or np.isinf(depth) or depth <= 0.1:
                    return

                # 3D 복원 계산 (카메라 광학 좌표계 기준)
                X_3d = (target_u - self.cx) * depth / self.fx
                Y_3d = (target_v - self.cy) * depth / self.fy
                Z_3d = depth

                self.get_logger().info(
                    f"Target Found -> Pixel: ({target_u}, {target_v}) | "
                    f"3D Coord (Camera Frame): X={X_3d:.3f}m, Y={Y_3d:.3f}m, Z={Z_3d:.3f}m"
                )

                # ===== [내용 추가] 3D 좌표 기반 TF 발행 로직 =====
                # t = TransformStamped()

                # # 타임스탬프와 부모 프레임 ID는 깊이 영상의 헤더 정보를 동적으로 추적하여 일치시킵니다.
                # # (Gazebo 설정에 따라 camera_link_optical 혹은 camera_depth_frame 등으로 자동 맵핑됩니다.)
                # t.header.stamp = self.latest_depth_msg.header.stamp
                # t.header.frame_id = self.latest_depth_msg.header.frame_id
                # t.child_frame_id = 'target_object'

                # # 계산된 3D 실물 좌표 대입
                # t.transform.translation.x = X_3d
                # t.transform.translation.y = Y_3d
                # t.transform.translation.z = Z_3d

                # # 별도의 회전이 없는 포인트 데이터이므로 기본 쿼터니언(회전 없음) 설정
                # t.transform.rotation.x = 0.0
                # t.transform.rotation.y = 0.0
                # t.transform.rotation.z = 0.0
                # t.transform.rotation.w = 1.0

                # # TF 배포 실행
                # self.tf_broadcaster.sendTransform(t)
                
                # ===== [수정 구간] NumPy 타입을 순수 Python float로 강제 캐스팅 =====
                t = TransformStamped()

                t.header.stamp = self.latest_depth_msg.header.stamp
                # [수정] 수신된 메시지 이름을 쓰지 않고, URDF TF 트리에 존재하는 광학 프레임 이름을 명시
                # (본인의 URDF에 정의된 카메라 optical 프레임 명칭으로 변경하세요)
                t.header.frame_id = 'camera_optical_frame' 
                # t.header.frame_id = self.latest_depth_msg.header.frame_id
                t.child_frame_id = 'target_object'
                
                # float() 처리를 통해 PyFloat_Check 어설션 에러를 방지합니다.
                t.transform.translation.x = float(X_3d)
                t.transform.translation.y = float(Y_3d)
                t.transform.translation.z = float(Z_3d)

                # 회전값 대입
                t.transform.rotation.x = 0.0
                t.transform.rotation.y = 0.0
                t.transform.rotation.z = 0.0
                t.transform.rotation.w = 1.0

                # TF 배포 실행
                self.tf_broadcaster.sendTransform(t)

        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge Error: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = TargetTracker3D()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
