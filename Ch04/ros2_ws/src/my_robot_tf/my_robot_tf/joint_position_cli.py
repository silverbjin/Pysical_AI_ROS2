"""4.7절: Gazebo joint1/joint2 위치 제어 명령 발행자 (시뮬레이션 전용)."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

from .joint_command_math import target_position


class JointPositionClient(Node):
    def __init__(self):
        super().__init__("joint_position_client")
        self.declare_parameter("joint_name", "joint1")
        self.declare_parameter("amplitude", 0.785)
        joint_name = self.get_parameter("joint_name").value
        amplitude = self.get_parameter("amplitude").value
        # 첫 제어 콜백 이전에 관절명/목표 제한을 검사한다.
        target_position(joint_name, True, amplitude)
        self.joint_name = joint_name
        self.amplitude = amplitude
        self.publisher = self.create_publisher(
            Float64, f"/{joint_name}/cmd_pos", 10
        )
        self.positive = False
        self.timer = self.create_timer(2.0, self.publish_target)

    def publish_target(self):
        command = Float64()
        command.data = target_position(
            self.joint_name, self.positive, self.amplitude
        )
        self.publisher.publish(command)
        self.get_logger().info(
            f"Published {self.joint_name}: {command.data:.3f} rad"
        )
        self.positive = not self.positive


def main():
    rclpy.init()
    node = None
    try:
        node = JointPositionClient()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
