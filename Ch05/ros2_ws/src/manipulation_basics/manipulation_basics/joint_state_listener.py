import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math

class JointStateListener(Node):
    def __init__(self):
        super().__init__('joint_state_listener')
        
        # 1. 서브스크라이버 생성
        # 토픽: /joint_states
        # 메시지 타입: JointState
        # QoS Profile: 10 (일반적인 센서 데이터용)
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10
        )
        self.subscription  # prevent unused variable warning

        # 모니터링할 타겟 관절 이름
        self.target_joint = 'joint2'
        
        self.get_logger().info(f'Listening to joint states... Monitoring: {self.target_joint}')

    def listener_callback(self, msg):
        # 2. 데이터 파싱
        # msg.name 리스트에서 'joint2'가 몇 번째 인덱스인지 찾는다.
        try:
            index = msg.name.index(self.target_joint)
        except ValueError:
            # 타겟 관절이 메시지에 없으면 무시
            return

        # 3. 해당 인덱스의 위치(Position)와 속도(Velocity) 추출
        current_pos = msg.position[index]
        current_vel = msg.velocity[index] if msg.velocity else 0.0
        
        # 라디안을 알기 쉬운 '도(Degree)'로 변환
        current_pos_deg = math.degrees(current_pos)

        # 4. 결과 출력
        # f-string을 이용해 소수점 둘째 자리까지 깔끔하게 출력
        self.get_logger().info(
            f'Joint: {self.target_joint} | '
            f'Pos: {current_pos:.4f} rad ({current_pos_deg:.2f} deg) | '
            f'Vel: {current_vel:.4f} rad/s'
        )

def main(args=None):
    rclpy.init(args=args)
    node = JointStateListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
