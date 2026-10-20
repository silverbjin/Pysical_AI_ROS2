"""Real rclpy lifecycle and command publication boundary tests, without an engine."""
from pathlib import Path
import sys
import time

import rclpy
from integrated_robot_interfaces.srv import SetMode
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2_ws/src/integrated_robot_runtime'))
from integrated_robot_runtime.locomotion import LocomotionNode


def test_unsafe_activation_stale_stop_and_inactive_publication_gate():
    rclpy.init(domain_id=136)
    node = LocomotionNode()
    observer = Node('lifecycle_test_observer')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(observer)
    commands = []
    observer.create_subscription(Float64MultiArray, '/leg_position_controller/commands',
                                 lambda msg: commands.append(list(msg.data)), 100)

    def pump(duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=0.01)

    try:
        node.trigger_configure()
        node.trigger_activate()
        assert not node.enabled, 'activation must fail without fresh measured joints'
        message = JointState()
        message.name = [f'{leg}_{joint}_joint' for leg in ('fr', 'fl', 'rr', 'rl')
                        for joint in ('hip', 'thigh', 'calf')] + [f'arm_joint_{i}' for i in range(1, 7)]
        message.position = [0.0, -0.5, 1.0] * 4 + [0.0] * 6
        message.header.stamp = node.get_clock().now().to_msg()
        node.on_joints(message)
        node.trigger_activate()
        assert node.enabled
        pump(0.25)
        assert commands and all(len(command) == 12 for command in commands)
        # Missing arm positions invalidate the whole safety gate and latch STOP.
        message.name = message.name[:12]
        message.position = message.position[:12]
        message.header.stamp = node.get_clock().now().to_msg()
        node.on_joints(message)
        pump(0.1)
        assert node.mode == 'STOP'
        count = len(commands)
        pump(0.1)
        assert len(commands) == count
        assert not node.set_mode(SetMode.Request(mode='STAND'), SetMode.Response()).accepted
        node.trigger_deactivate()
        assert not node.enabled
        pump(0.1)
        assert len(commands) == count
    finally:
        executor.shutdown()
        node.destroy_node()
        observer.destroy_node()
        rclpy.shutdown()
