import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class JointControlClient(Node):
    def __init__(self):
        super().__init__('joint_control_client')
        
        # 1. 퍼블리셔 생성
        # Gazebo 브릿지를 통해 전달될 토픽으로 명령을 보낸다.
        self.joint2_pub = self.create_publisher(
            Float64, 
            '/joint2/cmd_pos', # 브릿지에서 매핑할 짧은 이름
            10
        )
        
        # 2. 2초마다 목표 각도를 번갈아 전송하는 타이머
        self.timer = self.create_timer(2.0, self.timer_callback)
        self.toggle = False

    def timer_callback(self):
        msg = Float64()
        if self.toggle:
            msg.data = 0.785  # 약 45도 (라디안 단위)
            self.get_logger().info('Sending command: 45 degrees')
        else:
            msg.data = -0.785 # 약 -45도
            self.get_logger().info('Sending command: -45 degrees')
        
        self.joint2_pub.publish(msg)
        self.toggle = not self.toggle

def main():
    rclpy.init()
    node = JointControlClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
