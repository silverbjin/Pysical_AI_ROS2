"""Simulation-only odometry input adapter; never subscribes to cmd_vel."""
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry

from my_quadruped_bot.odometry_observation import ObservationStream


class SimOdometry(Node):
    """Publish observations; do not synthesize motion during sensor loss."""

    def __init__(self):
        super().__init__('sim_odometry')
        self.publisher = self.create_publisher(Odometry, '/odom/raw', 10)
        self.subscription = self.create_subscription(
            Odometry, '/simulation/odom', self.on_observation, qos_profile_sensor_data)
        self.stream = ObservationStream()
        self.last_error = None
        self.get_logger().info('SIMULATION ONLY: Gazebo model observations -> /odom/raw')

    def on_observation(self, message):
        try:
            observation = self.stream.accept(message)
        except ValueError as error:
            if str(error) != self.last_error:
                self.get_logger().error(str(error))
                self.last_error = str(error)
            return
        self.last_error = None
        if observation is not None:
            self.publisher.publish(observation)


def main(args=None):
    rclpy.init(args=args)
    node = SimOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
