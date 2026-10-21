"""Conservative, simulation-time-gated Ch05 Hello Robot trajectory publisher."""

import rclpy
from builtin_interfaces.msg import Duration
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from manipulation_basics.wave_profile import JOINT_NAMES, READY_POSE, pose_reached, wave_target


class WaveHelloNode(Node):
    """Wait for state, move to a safe ready pose, then wave at 20 Hz."""

    def __init__(self):
        super().__init__('wave_hello_node')
        if not self.get_parameter('use_sim_time').value:
            raise RuntimeError('simulation time required: --ros-args -p use_sim_time:=true')
        self.pub = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10)
        self.sub = self.create_subscription(
            JointState, '/joint_states', self.on_state, 10)
        self.latest_joint_positions = None
        self.last_state_time = None
        self.phase = 'WAITING'
        self.ready_start = None
        self.wave_start = None
        self.timer = self.create_timer(0.05, self.timer_callback)
        self.get_logger().info('Waiting for /clock, joint states and controller subscriber')

    def on_state(self, msg):
        positions = dict(zip(msg.name, msg.position))
        if all(name in positions for name in JOINT_NAMES):
            self.latest_joint_positions = tuple(positions[name] for name in JOINT_NAMES)
            self.last_state_time = self.get_clock().now().nanoseconds / 1e9

    def publish_goal(self, positions, velocities, duration_sec):
        msg = JointTrajectory()
        msg.joint_names = list(JOINT_NAMES)
        msg.header.stamp = self.get_clock().now().to_msg()
        point = JointTrajectoryPoint()
        point.positions = list(positions)
        point.velocities = list(velocities)
        point.time_from_start = Duration(
            sec=int(duration_sec), nanosec=int(round((duration_sec % 1) * 1e9)))
        msg.points = [point]
        self.pub.publish(msg)

    def timer_callback(self):
        now = self.get_clock().now().nanoseconds / 1e9
        if now <= 0 or self.pub.get_subscription_count() == 0:
            return
        if (self.last_state_time is None or self.latest_joint_positions is None
                or now - self.last_state_time > 0.5):
            # With stale feedback, stop issuing new trajectories rather than guess.
            if self.phase != 'WAITING':
                self.get_logger().error('Joint feedback stale; stopping wave publisher')
                self.timer.cancel()
            return
        if self.phase == 'WAITING':
            self.publish_goal(READY_POSE, [0.0] * 4, 3.0)
            self.ready_start = now
            self.phase = 'READY'
            self.get_logger().info('Moving to ready pose over 3 seconds')
        elif self.phase == 'READY':
            if now - self.ready_start < 3.0:
                return
            if pose_reached(self.latest_joint_positions):
                self.wave_start = now
                self.phase = 'WAVING'
                self.get_logger().info('Ready pose confirmed; beginning wave')
            elif now - self.ready_start >= 6.0:
                self.get_logger().error('Ready pose tolerance not achieved; aborting')
                self.timer.cancel()
        elif self.phase == 'WAVING':
            if now < self.wave_start:
                # Gazebo reset / backwards clock jump: do not replay stale motion.
                self.get_logger().error('Simulation time reset; stopping wave publisher')
                self.timer.cancel()
                return
            positions, velocities = wave_target(now - self.wave_start)
            self.publish_goal(positions, velocities, 0.15)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = WaveHelloNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
