#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped, TransformStamped
from tf2_ros import TransformBroadcaster, Buffer, TransformListener
from tf2_ros import TransformException
import numpy as np

class TargetTracker2D(Node):
    def __init__(self):
        super().__init__('target_tracker_2d')

        # 1. TF Listener 및 Broadcaster 초기화
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tf_broadcaster = TransformBroadcaster(self)

        # 2. 2D 픽셀 Subscriber 설정 (Depth 구독은 제거됨)
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

        # 사용할 기준 프레임 설정
        self.base_frame = 'base_link'
        self.camera_frame = 'camera_optical_frame'

        self.get_logger().info('Target Tracker 2D (Ray-Plane Intersection) Initialized.')

    def quaternion_to_rotation_matrix(self, q):
        """쿼터니언을 3x3 회전 행렬로 변환하는 헬퍼 함수"""
        x, y, z, w = q.x, q.y, q.z, q.w
        return np.array([
            [1 - 2*y*y - 2*z*z,     2*x*y - 2*z*w,     2*x*z + 2*y*w],
            [    2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z,     2*y*z - 2*x*w],
            [    2*x*z - 2*y*w,     2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
        ])

    def pixel_callback(self, msg):
        # 객체 인식 실패 시 예외 처리
        if msg.point.x == -1 or msg.point.y == -1:
            return

        target_u = msg.point.x
        target_v = msg.point.y

        # 1. TF Buffer에서 base_link 대비 카메라의 현재 위치 및 자세 조회
        try:
            # 타임스탬프를 0으로 설정하여 버퍼에 있는 가장 최신 TF를 가져옵니다.
            trans = self.tf_buffer.lookup_transform(
                self.base_frame, 
                self.camera_frame, 
                rclpy.time.Time()
            )
        except TransformException as ex:
            self.get_logger().warn(f'Could not transform {self.base_frame} to {self.camera_frame}: {ex}')
            return

        # 2. 카메라 광학 좌표계 기준 방향 벡터 (v_c) 계산
        x_c = (target_u - self.cx) / self.fx
        y_c = (target_v - self.cy) / self.fy
        z_c = 1.0
        v_c = np.array([x_c, y_c, z_c])

        # 3. 로봇(base_link) 기준 좌표계로 변환을 위한 회전 및 평행 이동 추출
        R_cam_to_base = self.quaternion_to_rotation_matrix(trans.transform.rotation)
        P_cam_pos = np.array([
            trans.transform.translation.x,
            trans.transform.translation.y,
            trans.transform.translation.z
        ])

        # 카메라의 3D 방향 벡터를 base_link 기준으로 회전 (v_b)
        v_b = np.dot(R_cam_to_base, v_c)

        # 4. 지면 교점(Ray-Plane Intersection) 계산
        # 광선이 하늘을 향하거나 완벽한 수평인 경우 지면(Z=0)과 만나지 않음
        if v_b[2] >= 0:
            self.get_logger().debug('Ray is pointing upwards. No ground intersection.')
            return

        # t = -Z_0 / V_z 공식 적용
        t = -P_cam_pos[2] / v_b[2]

        # 최종 3D 좌표 계산 (base_link 기준)
        X_base = P_cam_pos[0] + t * v_b[0]
        Y_base = P_cam_pos[1] + t * v_b[1]
        Z_base = 0.0  # 지면

        self.get_logger().info(
            f"Target 2D Found -> X={X_base:.3f}m, Y={Y_base:.3f}m, Z={Z_base:.3f}m (base_link ref)"
        )

        # 5. 계산된 3D 좌표를 base_link 기준으로 TF 발행
        t_msg = TransformStamped()
        t_msg.header.stamp = self.get_clock().now().to_msg()
        
        # 부모 프레임을 base_link로 설정 (RViz 시각화 및 제어 로직 직결)
        t_msg.header.frame_id = self.base_frame
        t_msg.child_frame_id = 'target_object'

        t_msg.transform.translation.x = float(X_base)
        t_msg.transform.translation.y = float(Y_base)
        t_msg.transform.translation.z = float(Z_base)

        t_msg.transform.rotation.x = 0.0
        t_msg.transform.rotation.y = 0.0
        t_msg.transform.rotation.z = 0.0
        t_msg.transform.rotation.w = 1.0

        self.tf_broadcaster.sendTransform(t_msg)

def main(args=None):
    rclpy.init(args=args)
    node = TargetTracker2D()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
