"""Combined engine startup waits for measured controller states, not a timer guess."""
from controller_manager_msgs.msg import ControllerState
from controller_manager_msgs.srv import ListControllers
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from integrated_robot_runtime.state_manager import StateManager


def test_controller_gate_keeps_spinning_and_requires_all_four_active():
    rclpy.init(domain_id=153)
    node, peer, executor = StateManager(), Node('controller_gate_peer'), SingleThreadedExecutor()
    requests = []
    try:
        names = ['joint_state_broadcaster', 'leg_position_controller',
                 'arm_trajectory_controller', 'gripper_position_controller']

        def listing(request, response):
            requests.append(True)
            response.controller = [ControllerState(name=name, state=(
                'inactive' if len(requests) == 1 and name == names[-1] else 'active')) for name in names]
            return response

        service = peer.create_service(ListControllers, '/controller_manager/list_controllers', listing)
        executor.add_node(node)
        executor.add_node(peer)
        node.wait_controllers(timeout=3.)
        assert len(requests) >= 2
    finally:
        executor.shutdown()
        node.destroy_node()
        peer.destroy_node()
        rclpy.shutdown()
