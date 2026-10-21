import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class StandUpNode(Node):
    def __init__(self):
        super().__init__('stand_up_node')
        
        # 방법 C 기준 기립 목표 각도
        self.target_pose = {
            'hip': 0.0,
            'thigh': -0.6,
            'calf': 1.2
        }
        
        # 명령 소유권: 다른 실습이 제어할 한 관절을 명시적으로 제외할 수 있다.
        self.declare_parameter('exclude_joint', '')
        self.exclude_joint = str(self.get_parameter('exclude_joint').value)
        self.declare_parameter('ramp_seconds', 2.0)
        self.ramp_seconds = float(self.get_parameter('ramp_seconds').value)
        if not (0.1 <= self.ramp_seconds <= 30.0):
            raise ValueError('ramp_seconds must be between 0.1 and 30.0')
        self._start_ns = self.get_clock().now().nanoseconds

        joints = [
            'fr_hip', 'fr_thigh', 'fr_calf',
            'fl_hip', 'fl_thigh', 'fl_calf',
            'rr_hip', 'rr_thigh', 'rr_calf',
            'rl_hip', 'rl_thigh', 'rl_calf'
        ]
        
        if self.exclude_joint and self.exclude_joint not in joints:
            raise ValueError(f'Unknown joint to exclude: {self.exclude_joint}')

        self.pubs = {}
        for j in joints:
            if j == self.exclude_joint:
                continue
            # [수정] ros2 topic list에 찍힌 실제 주소와 100% 일치시킴 (/0/ 제거)
            topic_name = f'/model/my_quadruped/joint/{j}_joint/cmd_pos'
            self.pubs[j] = self.create_publisher(Float64, topic_name, 10)
            
        # [추가] 0.1초(10Hz)마다 목표 각도를 지속적으로 쏴주는 타이머 생성
        self.timer = self.create_timer(0.1, self.publish_callback)
        self.get_logger().info('Stand Up Node has been started!')

    def publish_callback(self):
        now_ns = self.get_clock().now().nanoseconds
        if now_ns < self._start_ns:
            # Sim time reset: do not keep using an old timestamp.
            self._start_ns = now_ns
        elapsed = max(0.0, (now_ns - self._start_ns) * 1e-9)
        alpha = min(1.0, elapsed / self.ramp_seconds)
        for j, pub in self.pubs.items():
            msg = Float64()
            # joint 이름 구조에 따라 목표값 매핑 (hip, thigh, calf 구분)
            if 'hip' in j:
                msg.data = alpha * self.target_pose['hip']
            elif 'thigh' in j:
                msg.data = alpha * self.target_pose['thigh']
            elif 'calf' in j:
                msg.data = alpha * self.target_pose['calf']
                
            pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = StandUpNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down Stand Up Node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()