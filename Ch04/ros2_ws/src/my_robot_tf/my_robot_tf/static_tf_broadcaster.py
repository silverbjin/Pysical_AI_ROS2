import sys
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

def euler_to_quaternion(roll, pitch, yaw):
    """
    오일러 각(Roll, Pitch, Yaw)을 쿼터니언(x, y, z, w)으로 변환하는 헬퍼 함수
    입력: 라디안 단위의 각도
    출력: 쿼터니언 리스트 [x, y, z, w]
    """
    qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
    qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
    qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    return [qx, qy, qz, qw]

class StaticFramePublisher(Node):
    """
    정적 좌표 변환(Static TF)을 방송하는 노드
    """
    def __init__(self):
        super().__init__('static_tf_broadcaster_node')

        # TF2의 핵심: 정적 변환 브로드캐스터 생성
        self._tf_publisher = StaticTransformBroadcaster(self)

        # 변환 정보를 담을 메시지 생성
        self.make_transforms()

    def make_transforms(self):
        t = TransformStamped()

        # 1. 시간 정보 입력
        # 정적 변환이라도 '현재 시간'을 찍어주는 것이 관례이다.
        t.header.stamp = self.get_clock().now().to_msg()
        
        # 2. 프레임 ID 설정 (족보 정리)
        t.header.frame_id = 'base_link'    # 부모: 로봇 몸통
        t.child_frame_id = 'lidar_sensor_link' # 자식: LiDAR 센서

        # 3. 위치 정보 (Translation) 설정 (단위: 미터)
        # 로봇 중심에서 앞으로 0.1m, 위로 0.2m 위치에 센서가 있음
        t.transform.translation.x = 0.1
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.2

        # 4. 회전 정보 (Rotation) 설정
        # 센서가 뒤집혀 있거나 회전해 있다면 여기서 설정
        # 예: Roll 0, Pitch 0, Yaw 0 (정면 바라봄)
        quat = euler_to_quaternion(0.0, 0.0, 0.0)

        t.transform.rotation.x = quat[0]
        t.transform.rotation.y = quat[1]
        t.transform.rotation.z = quat[2]
        t.transform.rotation.w = quat[3]

        # 5. 브로드캐스트 (전송)
        # sendTransform은 한 번 호출되면 ROS 2 시스템에 래칭(Latching)된다.
        # 즉, 새로운 리스너가 들어올 때마다 자동으로 정보를 준다.
        self._tf_publisher.sendTransform(t)
        self.get_logger().info(f'Static TF Published: {t.header.frame_id} -> {t.child_frame_id}')

def main():
    rclpy.init()
    node = StaticFramePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
