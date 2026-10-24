"""Actual DDS: two executor workers alone cannot bypass a shared callback group.
This controlled blocking-work fixture is NOT a native safety/locomotion verdict.
"""
from threading import Event, Thread
import importlib
import time
import pytest

import rclpy
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from std_srvs.srv import Trigger
from geometry_msgs.msg import Point
from integrated_robot_interfaces.msg import FootContacts

from integrated_robot_navigation.crawl_controller import CrawlController


@pytest.mark.parametrize('observe', ['clock', 'contacts'])
def test_ingress_can_update_while_default_control_group_owns_model_lock(observe):
    context = Context()
    rclpy.init(context=context)
    node = CrawlController(context=context,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],
        parameter_overrides=[Parameter('use_sim_time',value=True),
            Parameter('validation_mode',value=True),Parameter('control_clock_mode',value='relay100')])
    peer = Node('clock_dispatch_peer',context=context)
    from integrated_robot_navigation.clock_execution import make_control_executor
    executor = make_control_executor(node)
    assert isinstance(executor,MultiThreadedExecutor)
    entered, release, finished = Event(), Event(), Event()
    def controlled_work(request,response):
        with node.lock:
            entered.set()
            release.wait(1.)
            finished.set()
        response.success = True
        return response
    node.create_service(Trigger,'/clock_dispatch_test_work',controlled_work)
    source = peer.create_publisher(Clock,'/navigation/control_clock',qos_profile_sensor_data)
    contacts = peer.create_publisher(FootContacts,'/navigation/foot_contacts',qos_profile_sensor_data)
    client = peer.create_client(Trigger,'/clock_dispatch_test_work')
    executor.add_node(node); executor.add_node(peer)
    thread = Thread(target=executor.spin)
    thread.start()
    def publish_until(stamp,predicate,seconds):
        deadline = time.monotonic()+seconds
        while not predicate() and time.monotonic() < deadline:
            msg = Clock()
            msg.clock.sec = stamp
            source.publish(msg)
            time.sleep(.005)
        return predicate()
    try:
        assert client.wait_for_service(timeout_sec=1.)
        assert publish_until(1,lambda: node.get_clock().now().nanoseconds == 1000000000,1.)
        assert len(peer.get_publishers_info_by_topic('/navigation/control_clock')) == 1
        subscriptions = peer.get_subscriptions_info_by_topic('/navigation/control_clock')
        assert [item.node_name for item in subscriptions] == ['crawl_controller'], \
            'isolation must reuse the one TimeSource subscriber, not duplicate it'
        future = client.call_async(Trigger.Request())
        assert entered.wait(1.)
        if observe == 'clock':
            assert publish_until(2,lambda: node.get_clock().now().nanoseconds == 2000000000,.15), \
                'real clock callback starved behind the mutually-exclusive control group'
        else:
            msg = FootContacts(names=['FL','FR','RL','RR'], normal_forces=[30.]*4,
                touching=[True]*4, points=[Point(z=-.4) for _ in range(4)])
            msg.header.stamp.sec = 1
            msg.header.frame_id = 'base_link'
            before = time.monotonic_ns()
            deadline = time.monotonic()+.15
            while not node.contact_ingress and time.monotonic() < deadline:
                contacts.publish(msg)
                time.sleep(.005)
            assert node.contact_ingress, 'healthy contact ingress starved behind control work/model lock'
            sample = node.inbox.pending['contacts'][1000000000]
            assert sample.data['forces'] == (30.,30.,30.,30.)
            assert before <= sample.received_ns <= time.monotonic_ns()
            assert node.machine is None and not node.active, 'ingress must not configure/activate a machine'
        assert not finished.is_set(), 'ingress must not depend on completing the blocked work'
        release.set()
        deadline = time.monotonic()+1.
        while not future.done() and time.monotonic() < deadline:
            time.sleep(.005)
        assert future.done() and future.result().success
    finally:
        release.set()
        executor.shutdown(timeout_sec=2.)
        thread.join(timeout=2.)
        assert not thread.is_alive()
        node.destroy_node(); peer.destroy_node(); context.try_shutdown()


def test_native_executor_keeps_single_worker_and_relay_requires_explicit_validation():
    assert importlib.util.find_spec('integrated_robot_navigation.clock_execution'), 'owned executor selection missing'
    from integrated_robot_navigation.clock_execution import make_control_executor
    from rclpy.executors import SingleThreadedExecutor
    import pytest
    context = Context()
    rclpy.init(context=context)
    node = CrawlController(context=context)
    executor = None
    try:
        executor = make_control_executor(node)
        assert isinstance(executor,SingleThreadedExecutor), 'native default scheduling must remain unchanged'
        with pytest.raises(ValueError,match='validation'):
            bad = CrawlController(context=context,parameter_overrides=[
                Parameter('control_clock_mode',value='relay100')])
            bad.destroy_node()
    finally:
        if executor is not None:
            executor.shutdown(timeout_sec=2.)
        node.destroy_node(); context.try_shutdown()
