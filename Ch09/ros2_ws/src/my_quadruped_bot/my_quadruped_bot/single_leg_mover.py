# my_quadruped_bot/my_quadruped_bot/single_leg_mover.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import math

class SingleLegMover(Node):
    def __init__(self):
        super().__init__('single_leg_mover')
        
        # 1. 제어할 대상 토픽 (FR Thigh Joint)
        # 브리지의 비대칭 매핑 덕분에 /0/이 없는 깔끔한 ROS 2 표준 주소를 사용합니다.
        self.topic_name = '/model/my_quadruped/joint/fr_thigh_joint/cmd_pos'
        self.pub = self.create_publisher(Float64, self.topic_name, 10)
        
        # 2. 타이머 설정 (100Hz = 0.01초 간격으로 조밀하게 궤적 생성)
        self.timer_period = 0.01
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 3. 사인파 파라미터 설정
        self.time = 0.0           # 누적 시간
        
        # [수정] 방법 C의 기립 중심점인 -0.6 rad를 오프셋으로 설정합니다.
        self.offset = -0.6        
        self.amplitude = 0.3      # 흔드는 범위 (+- 0.3 rad)
        self.frequency = 1.0      # 주파수 (1Hz = 1초에 한 번 부드럽게 왕복)
        
        self.get_logger().info(f"Start moving leg on topic: {self.topic_name}")

    def timer_callback(self):
        # 4. 사인파 수식 적용
        # target_pos = 중심(-0.6) + 진폭(0.3) * sin(2 * pi * 주파수(1.0) * 시간)
        current_angle = self.offset + self.amplitude * math.sin(2 * math.pi * self.frequency * self.time)
        
        # 5. 메시지 발행
        msg = Float64()
        msg.data = current_angle
        self.pub.publish(msg)
        
        # 6. 시간 업데이트
        self.time += self.timer_period

def main(args=None):
    rclpy.init(args=args)
    node = SingleLegMover()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()