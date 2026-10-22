"""A rehearsal input keeps its capture header across a delayed ROS clock delivery."""
import importlib.util
from pathlib import Path
import threading
import time

import rclpy
from integrated_robot_interfaces.action import PickObject
from integrated_robot_runtime.policy import validate_target
from rclpy.action import ActionServer, GoalResponse
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rosgraph_msgs.msg import Clock


def test_rehearsal_preserves_capture_while_server_clock_catches_up():
    """Sending immediately makes a valid synthetic capture look 60ms future-dated."""
    spec = importlib.util.spec_from_file_location('architecture_probe',
        Path(__file__).resolve().parents[1]/'scripts/verify_architecture_13_3.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rclpy.init(domain_id=163)
    peer, probe = Node('architecture_clock_peer'), module.Probe()
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    publisher = peer.create_publisher(Clock, '/clock', 1)
    stop = threading.Event()
    deliveries = []
    started = [None]

    def accept(goal):
        # A controlled delayed server clock sample, not a relaxed age predicate.
        elapsed = time.monotonic()-started[0]
        server_now = 10.0 if elapsed < .08 else 10.16
        stamp = goal.target_pose.header.stamp.sec+goal.target_pose.header.stamp.nanosec*1e-9
        error = validate_target('cup', 'base_link', stamp, server_now,
                                [.3, 0., .4], [0., 0., 0., 1.], True)
        deliveries.append((stamp, server_now, error))
        return GoalResponse.REJECT if error else GoalResponse.ACCEPT

    def execute(handle):
        handle.abort()
        return PickObject.Result(success=False, error_code=PickObject.Result.NOT_IMPLEMENTED)

    server = ActionServer(peer, PickObject, '/manipulation_node/pick_object', execute,
                          goal_callback=accept)

    def spin():
        while not stop.is_set():
            executor.spin_once(timeout_sec=.005)

    thread = threading.Thread(target=spin)
    thread.start()
    try:
        assert probe.pick.wait_for_server(timeout_sec=3)
        message = Clock()
        message.clock.sec, message.clock.nanosec = 10, 60_000_000
        deadline = time.monotonic()+3
        while probe.get_clock().now().nanoseconds != 10_060_000_000:
            assert time.monotonic() < deadline
            publisher.publish(message)
            rclpy.spin_once(probe, timeout_sec=.02)
        started[0] = time.monotonic()
        handle = probe.goal()
        assert handle.accepted, deliveries
        result = handle.get_result_async()
        probe.until(result.done)
        assert len(deliveries) == 1, 'no retry is allowed'
        assert deliveries[0][0] == 10.06, 'do not restamp the capture'
        assert deliveries[0][1] == 10.16
        assert not result.result().result.success
    finally:
        stop.set()
        thread.join(timeout=3)
        executor.shutdown(timeout_sec=3)
        probe.destroy_node()
        server.destroy()
        peer.destroy_node()
        rclpy.try_shutdown()
