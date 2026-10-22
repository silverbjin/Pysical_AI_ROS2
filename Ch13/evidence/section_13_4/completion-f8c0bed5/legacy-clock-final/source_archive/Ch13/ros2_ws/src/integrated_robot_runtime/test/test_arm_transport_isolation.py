"""Real action responses must progress while the parent's callback pool is busy."""
import threading
import time

import rclpy
import pytest
from control_msgs.action import FollowJointTrajectory
from rclpy.action import ActionServer
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from trajectory_msgs.msg import JointTrajectoryPoint

from integrated_robot_runtime.common import DrainingExecutor
from integrated_robot_runtime.manipulation import ManipulationNode
from integrated_robot_runtime.policy import ARM_NAMES


def test_real_result_arrives_without_parent_pool_capacity():
    rclpy.init(domain_id=149)
    node = ManipulationNode()
    peer = Node('independent_controller_boundary')
    executed, release, stopping = threading.Event(), threading.Event(), threading.Event()
    occupied = threading.Barrier(5)
    record = None

    def execute(handle):
        executed.set()
        handle.succeed()
        return FollowJointTrajectory.Result(error_code=0)

    server = ActionServer(peer, FollowJointTrajectory,
        '/arm_trajectory_controller/follow_joint_trajectory', execute)
    parent = DrainingExecutor(num_threads=4)
    controller = SingleThreadedExecutor()
    parent.add_node(node)
    controller.add_node(peer)

    def spin(executor):
        while not stopping.is_set():
            executor.spin_once(timeout_sec=.01)

    threads = [threading.Thread(target=spin, args=(executor,))
               for executor in (parent, controller)]
    for thread in threads:
        thread.start()
    try:
        assert node.trajectory.wait_for_server(timeout_sec=3)

        def busy_parent_callback():
            occupied.wait(timeout=3)
            release.wait(timeout=3)

        for _ in range(4):
            parent.create_task(busy_parent_callback)
        occupied.wait(timeout=3)
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(ARM_NAMES)
        goal.trajectory.points = [JointTrajectoryPoint(positions=[0.]*6)]
        record = node.arm_owner.send(goal, now=time.monotonic(), timeout=2)
        assert executed.wait(timeout=1), 'real server did not execute the request'
        deadline = time.monotonic()+.5
        while not record.terminal and time.monotonic() < deadline:
            time.sleep(.005)
        assert record.terminal, node.arm_owner.snapshot()
        assert record.result.status == 4 and node.arm_owner.pending is None
        assert not release.is_set(), 'parent was released before the result proved isolation'
    finally:
        release.set()
        deadline = time.monotonic()+1
        while record is not None and not record.terminal and time.monotonic() < deadline:
            time.sleep(.005)
        stopping.set()
        for thread in threads:
            thread.join(timeout=3)
        parent.shutdown(timeout_sec=3)
        controller.shutdown(timeout_sec=3)
        node.destroy_node()
        assert not node.arm_transport.thread.is_alive()
        assert node.arm_transport.closed
        peer.destroy_node()
        rclpy.try_shutdown()


def test_action_receiver_ignores_sim_clock_and_stops_before_context():
    rclpy.init(domain_id=149)
    node = ManipulationNode(parameter_overrides=[Parameter('use_sim_time', value=True)])
    transport = node.arm_transport
    try:
        assert node.get_parameter('use_sim_time').value is True
        assert transport.node.get_parameter('use_sim_time').value is False
        assert transport.healthy
        node.destroy_node()
        assert not transport.healthy and not transport.thread.is_alive()
        assert rclpy.ok(), 'transport teardown must precede shared context teardown'
        transport.close()  # Normal shutdown may call the idempotent owner again.
    finally:
        if not transport.closed:
            node.destroy_node()
        rclpy.try_shutdown()


def test_failed_parent_constructor_leaves_no_action_receiver_thread():
    rclpy.init(domain_id=149)
    before = set(threading.enumerate())
    try:
        with pytest.raises(ValueError, match='canonical UUID'):
            ManipulationNode(parameter_overrides=[
                Parameter('trace_enabled', value=True), Parameter('trace_run_id', value='bad')])
        assert set(threading.enumerate()) == before
    finally:
        rclpy.try_shutdown()
