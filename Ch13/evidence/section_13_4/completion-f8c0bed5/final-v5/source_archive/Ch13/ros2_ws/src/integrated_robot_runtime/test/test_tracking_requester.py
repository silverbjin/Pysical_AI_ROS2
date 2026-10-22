"""Explicit launch opt-in requests at most one enable, never retries a refusal."""
import json
import time

from integrated_robot_interfaces.msg import TrackedTarget
import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import SetBool
from concurrent.futures import Future

from integrated_robot_runtime.policy import ARM_NAMES, LEG_NAMES, STAND
from integrated_robot_runtime.tracking_requester import TrackingRequester


@pytest.mark.parametrize('accepted', [True, False])
def test_waits_for_fresh_measurements_then_requests_once_even_after_refusal(accepted):
    rclpy.init(domain_id=152)
    node, peer, executor = TrackingRequester(), Node('requester_test_peer'), SingleThreadedExecutor()
    calls = []
    try:
        def toggle(request, response):
            calls.append(request.data)
            response.success, response.message = accepted, 'explicit boundary reply'
            return response

        service = peer.create_service(SetBool, '/manipulation_node/set_visual_tracking', toggle)
        executor.add_node(node)
        executor.add_node(peer)

        def pump(duration):
            end = time.monotonic()+duration
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.01)

        pump(.15)
        assert calls == []
        node.on_startup(String(data=json.dumps(dict(status='READY'))))
        joints = JointState(name=list(ARM_NAMES+LEG_NAMES), position=[0.]*6+list(STAND))
        joints.header.stamp = node.get_clock().now().to_msg()
        node.on_joints(joints)
        target = TrackedTarget(valid=True, status='TRACKED')
        target.header.stamp = node.get_clock().now().to_msg()
        node.on_target(target)
        pump(.3)
        assert calls == [True] and node.done and node.success is accepted
        target.header.stamp = node.get_clock().now().to_msg()
        node.on_target(target)
        pump(.3)
        assert calls == [True]
    finally:
        executor.shutdown()
        node.destroy_node()
        peer.destroy_node()
        rclpy.shutdown()


def test_late_enable_success_after_timeout_is_explicitly_disabled():
    rclpy.init(domain_id=152)
    node, peer, executor = TrackingRequester(), Node('late_request_peer'), SingleThreadedExecutor()
    calls = []
    try:
        def toggle(request, response):
            calls.append(request.data)
            response.success = True
            return response

        service = peer.create_service(SetBool, '/manipulation_node/set_visual_tracking', toggle)
        executor.add_node(node)
        executor.add_node(peer)
        assert node.client.wait_for_service(timeout_sec=2.)
        node.report(False, 'request deadline exceeded')
        future = Future()
        future.set_result(SetBool.Response(success=True, message='late acceptance'))
        node.response(future)
        end = time.monotonic()+.3
        while time.monotonic() < end:
            executor.spin_once(timeout_sec=.01)
        assert calls == [False] and not node.success
    finally:
        executor.shutdown()
        node.destroy_node()
        peer.destroy_node()
        rclpy.shutdown()
