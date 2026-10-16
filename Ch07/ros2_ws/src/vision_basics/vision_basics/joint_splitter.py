import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

class JointSplitter(Node):
    def __init__(self):
        super().__init__('joint_splitter')
        # 1. GUI 슬라이더가 쏘는 /joint_states 구독
        self.sub = self.create_subscription(JointState, '/joint_states', self.callback, 10)
        
        # 2. Gazebo 브리지용 퍼블리셔들을 딕셔너리로 자동 생성
        self.joints = ['joint1', 'joint2', 'joint3', 'joint4', 'joint_wrist', 'joint_finger1', 'joint_finger2']
        self.pubs = {
            name: self.create_publisher(Float64, f'/model/my_robot/{name}/cmd_pos', 10)
            for name in self.joints
        }

    def callback(self, msg):
        # /joint_states 메시지가 들어오면 관절 이름별로 매칭하여 개별 Float64 토픽으로 쪼개서 발행
        for name, position in zip(msg.name, msg.position):
            if name in self.pubs:
                float_msg = Float64()
                float_msg.data = position
                self.pubs[name].publish(float_msg)

def main(args=None):
    rclpy.init(args=args)
    node = JointSplitter()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()