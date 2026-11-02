"""State-cache burst reproduction over DDS, not native locomotion acceptance."""
import threading
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from builtin_interfaces.msg import Time
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_navigation.clock_execution import make_control_executor
from integrated_robot_navigation.crawl_controller import CrawlController


@pytest.mark.parametrize('fault', ['', 'original_sticky_fault'])
@pytest.mark.parametrize('mode', ['native', 'relay100'])
def test_first_guard_after_block_is_latest_original_state_not_queued_oldest(fault, mode):
    context = Context()
    rclpy.init(context=context, domain_id=166)
    node = CrawlController(context=context,
        cli_args=['--ros-args', '-r', '/clock:=/navigation/control_clock'] if mode == 'relay100' else [],
        parameter_overrides=[Parameter('use_sim_time', value=True),
            Parameter('validation_mode', value=True), Parameter('control_clock_mode', value=mode)])
    peer = Node('guard_latest_state_peer', context=context)
    executor = make_control_executor(node)
    entered, release, stopping = threading.Event(), threading.Event(), threading.Event()
    errors = []

    def blocked(request, response):
        entered.set()
        assert release.wait(3.)
        response.success = True
        return response

    node.create_service(Trigger, '/guard_latest_block', blocked, callback_group=node.sensor_group)
    clock = peer.create_publisher(Clock, '/navigation/control_clock' if mode == 'relay100' else '/clock',
        qos_profile_sensor_data)
    publisher = peer.create_publisher(MotionState, '/navigation/guard_state', 10)
    client = peer.create_client(Trigger, '/guard_latest_block')
    executor.add_node(node)
    executor.add_node(peer)

    def spin():
        try:
            while not stopping.is_set():
                executor.spin_once(timeout_sec=.01)
        except BaseException as error:
            errors.append(repr(error))

    thread = threading.Thread(target=spin)
    thread.start()
    try:
        deadline = time.monotonic()+2.
        while (publisher.get_subscription_count() != 1 or not client.service_is_ready()) and time.monotonic() < deadline:
            time.sleep(.005)
        assert publisher.get_subscription_count() == 1 and client.service_is_ready()
        clock.publish(Clock(clock=Time(sec=10)))
        while node.get_clock().now().nanoseconds != 10_000_000_000 and time.monotonic() < deadline:
            time.sleep(.005)
        assert node.get_clock().now().nanoseconds == 10_000_000_000
        future = client.call_async(Trigger.Request())
        assert entered.wait(1.)
        first_wall = time.monotonic_ns()
        for i in range(10):
            state = MotionState()
            state.header.stamp = Time(sec=9, nanosec=700_000_000+i*30_000_000)
            state.generation = 8
            state.model_sha256 = 'original-model'
            state.state = 'STAND'
            state.fault_reason = fault
            publisher.publish(state)
        time.sleep(.04)  # all offered samples reach DDS before the group resumes
        release.set()
        deadline = time.monotonic()+2.
        while not node.guard_receipts and time.monotonic() < deadline:
            time.sleep(.005)
        assert node.guard_receipts
        first = node.guard_receipts[0]
        assert first['stamp_ns'] == 9_970_000_000, 'control resumed with an obsolete queued state'
        assert first_wall <= first['received_ns'] <= time.monotonic_ns()
        assert first['source_system_ns'] > 0 and first['rmw_received_system_ns'] > 0
        assert first['callback_system_ns'] >= first['rmw_received_system_ns']
        with node.inbox_lock:
            state, receipt = node._gate_pending[9_970_000_000]
            assert state.generation == 8 and state.model_sha256 == 'original-model'
            assert state.fault_reason == fault
            assert receipt == first['received_ns']
        assert node.gate is None and node.machine is None
        # Latest delivery does not extend a source/receipt lease or waive loss.
        assert node._gate_valid(10_300_000_000, receipt+1) == (False, 'guard:ros_age')
        assert node._gate_valid(10_000_000_000, receipt+200_000_001) == (False, 'guard:wall_age')
    finally:
        release.set()
        stopping.set()
        executor.wake()
        thread.join(2.)
        assert not thread.is_alive()
        executor.shutdown(timeout_sec=2.)
        node.destroy_node()
        peer.destroy_node()
        context.try_shutdown()
        assert not errors, errors
