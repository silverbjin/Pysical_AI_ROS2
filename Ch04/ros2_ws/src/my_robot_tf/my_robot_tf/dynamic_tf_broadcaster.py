import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

# 쿼터니언 변환 함수는 필수적이므로 유틸리티처럼 계속 사용한다.
def euler_to_quaternion(roll, pitch, yaw):
    qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
    qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
    qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    return [qx, qy, qz, qw]

class DynamicFramePublisher(Node):
    def __init__(self):
        super().__init__('dynamic_tf_broadcaster_node')
        
        # 1. TransformBroadcaster 초기화
        # Static과 다르게 일반 'TransformBroadcaster'를 사용한다.
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 2. 타이머 설정
        # 30Hz 주기로 실행 (1초 / 30 = 약 0.033초마다 콜백 실행)
        self.timer_period = 0.033 
        self.timer = self.create_timer(self.timer_period, self.broadcast_timer_callback)
        
        # 로봇의 상태 변수 (각도)
        self.theta = 0.0
        self.radius = 2.0 # 회전 반경 2m

        self.get_logger().info("Dynamic TF Broadcaster Started. Turtles are circling...")

    def broadcast_timer_callback(self):
        # 메시지 객체 생성
        t = TransformStamped()

        # [중요] 타임스탬프 업데이트
        # 매 순간 현재 시간을 찍어서 보내야 한다.
        t.header.stamp = self.get_clock().now().to_msg()
        
        # 프레임 관계 설정
        t.header.frame_id = 'world'
        t.child_frame_id = 'turtle_frame'

        # 로봇의 위치 계산 (원 운동)
        # 매번 theta를 조금씩 증가시켜 위치를 바꾼다.
        self.theta += 0.05 # 각도 증가 속도 조절
        
        # 위치 정보 (Translation)
        t.transform.translation.x = self.radius * math.cos(self.theta)
        t.transform.translation.y = self.radius * math.sin(self.theta)
        t.transform.translation.z = 0.0 # 바닥 위를 움직임

        # 자세 정보 (Rotation)
        # 로봇이 진행 방향을 바라보게 하려면 Yaw 각도를 theta와 일치시킨다.
        # 여기에 90도(1.57 rad)를 더한 이유는 로봇 모델의 전방 축과 수학적 각도를 맞추기 위함이다.
        quat = euler_to_quaternion(0, 0, self.theta + 1.57)
        
        t.transform.rotation.x = quat[0]
        t.transform.rotation.y = quat[1]
        t.transform.rotation.z = quat[2]
        t.transform.rotation.w = quat[3]

        # TF 방송 송출
        self.tf_broadcaster.sendTransform(t)

def main():
    rclpy.init()
    node = DynamicFramePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
