"""Actual DDS: isolated ingress progresses while the serial model owner is busy.
This controlled blocking-work fixture is NOT a native safety/locomotion verdict.
"""
from threading import Event, Thread
import importlib
import time
import json
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
from integrated_robot_interfaces.msg import FootContacts,MotionState

from integrated_robot_navigation.crawl_controller import CrawlController


@pytest.mark.parametrize('observe', ['clock', 'contacts', 'guard', 'command'])
@pytest.mark.parametrize('g2_scope',[False,True])
def test_ingress_can_update_while_default_control_group_owns_model_lock(observe,g2_scope):
    context = Context()
    rclpy.init(context=context)
    node = CrawlController(context=context,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],
        parameter_overrides=[Parameter('use_sim_time',value=True),
            Parameter('validation_mode',value=True),Parameter('control_clock_mode',value='relay100'),
            Parameter('g2_validation_mode',value=g2_scope),
            Parameter('native_execution_profile',value=json.dumps(dict(control_clock='relay100',
                position_reference_mode='native',dart_contact='native',native_physics_sha256='a'*64)) if g2_scope else '')])
    peer = Node('clock_dispatch_peer',context=context)
    from integrated_robot_navigation.clock_execution import make_control_executor
    executor = make_control_executor(node)
    from rclpy.executors import SingleThreadedExecutor
    assert isinstance(executor,SingleThreadedExecutor if g2_scope else MultiThreadedExecutor)
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
    guard = peer.create_publisher(MotionState,'/navigation/guard_state',10)
    from geometry_msgs.msg import Twist
    command = peer.create_publisher(Twist,'/navigation/cmd_vel',10)
    client = peer.create_client(Trigger,'/clock_dispatch_test_work')
    executor.add_node(node); executor.add_node(peer)
    stopping=Event();dispatch_errors=[]
    def spin_owned_dispatch():
        try:
            while not stopping.is_set():executor.spin_once(timeout_sec=.01)
        except BaseException as error:dispatch_errors.append(repr(error))
    thread = Thread(target=spin_owned_dispatch)
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
        assert [item.node_name for item in subscriptions] == ['crawl_controller_ingress'], \
            'the original TimeSource must have one owned ingress subscriber, never a duplicate'
        future = client.call_async(Trigger.Request())
        assert entered.wait(1.)
        if observe == 'clock':
            assert publish_until(2,lambda: node.get_clock().now().nanoseconds == 2000000000,.15), \
                'real clock callback starved behind the mutually-exclusive control group'
        elif observe == 'contacts':
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
        elif observe == 'command':
            msg = Twist(); msg.linear.x = .01
            before = time.monotonic_ns()
            deadline = time.monotonic()+.15
            while node.command is None and time.monotonic()<deadline:
                command.publish(msg)
                time.sleep(.005)
            assert node.command is not None, 'final command ingress starved behind control work/model lock'
            assert node.command.data == (.01,0.,0.)
            assert before<=node.command.received_ns<=time.monotonic_ns()
            assert node.machine is None and not node.active
        else:
            msg = MotionState(state='FAULT',generation=3,model_sha256='original-model',
                              fault_reason='original fault must remain visible')
            msg.header.stamp.sec = 1
            msg.header.frame_id = 'base_link'
            before = time.monotonic_ns()
            deadline = time.monotonic()+.15
            while not node.guard_receipts and time.monotonic()<deadline:
                guard.publish(msg)
                time.sleep(.005)
            assert node.guard_receipts, 'state feedback must not starve behind model/control callbacks'
            cached,receipt = node._gate_pending[1000000000]
            assert cached.generation==3 and cached.model_sha256=='original-model'
            assert cached.fault_reason=='original fault must remain visible'
            assert before<=receipt<=time.monotonic_ns()
            assert node.gate is None and node.machine is None, 'ingress cannot select/interpret the mode'
        assert not finished.is_set(), 'ingress must not depend on completing the blocked work'
        release.set()
        deadline = time.monotonic()+1.
        while not future.done() and time.monotonic() < deadline:
            time.sleep(.005)
        assert future.done() and future.result().success
    finally:
        release.set()
        # Production stops dispatch before draining its pool. A fixture-owned
        # background spin must be joined first, otherwise it can submit into
        # the pool while DrainingExecutor closes that pool (full-suite warning).
        stopping.set();executor.wake()
        thread.join(timeout=2.)
        assert not thread.is_alive()
        executor.shutdown(timeout_sec=2.)
        node.destroy_node(); peer.destroy_node(); context.try_shutdown()
        assert not dispatch_errors,dispatch_errors


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
