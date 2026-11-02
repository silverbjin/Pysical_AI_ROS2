"""Real DDS ingress must not wait for the model owner's pool to dispatch.

No motor activation, synthetic ROS clock, or engine acceptance is claimed.
"""
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist, Point
from integrated_robot_interfaces.msg import FootContacts, MotionState
from rclpy.qos import qos_profile_sensor_data
from integrated_robot_navigation.crawl_controller import CrawlController


@pytest.mark.parametrize('stream',['guard','contacts','command'])
def test_relay_ingress_receives_original_data_without_dispatching_model_owner(stream):
    context=Context();rclpy.init(context=context)
    node=CrawlController(context=context,cli_args=['--ros-args','-r',
        '/navigation/guard_state:=/independent_ingress/guard'],parameter_overrides=[
        Parameter('validation_mode',value=True),Parameter('control_clock_mode',value='relay100')])
    peer=Node('independent_ingress_peer',context=context)
    if stream=='guard':
        topic='/independent_ingress/guard';kind=MotionState;qos=1
        msg=MotionState(state='FAULT',generation=7,model_sha256='original',fault_reason='retained')
        msg.header.stamp.sec=17;msg.header.frame_id='base_link'
        arrived=lambda:bool(node.guard_receipts)
    elif stream=='contacts':
        topic='/navigation/foot_contacts';kind=FootContacts;qos=qos_profile_sensor_data
        msg=FootContacts(names=['FL','FR','RL','RR'],normal_forces=[30.]*4,
            touching=[True]*4,points=[Point(z=-.4) for _ in range(4)])
        msg.header.stamp.sec=17;msg.header.frame_id='base_link'
        arrived=lambda:bool(node.contact_ingress)
    else:
        topic='/navigation/cmd_vel';kind=Twist;qos=10
        msg=Twist();msg.linear.x=.01
        arrived=lambda:node.command is not None
    pub=peer.create_publisher(kind,topic,qos)
    try:
        deadline=time.monotonic()+2.
        while pub.get_subscription_count()!=1 and time.monotonic()<deadline:time.sleep(.01)
        assert pub.get_subscription_count()==1,'exactly one ingress subscription required'
        before=time.monotonic_ns();deadline=time.monotonic()+.15
        while not arrived() and time.monotonic()<deadline:
            pub.publish(msg);time.sleep(.005)
        assert arrived(),'sensor ingress starved while the model executor was not dispatching'
        assert node.machine is None and not node.active and node.command_publication_count==0
        if stream=='guard':
            saved,receipt=node._gate_pending[17_000_000_000]
            assert saved==msg and before<=receipt<=time.monotonic_ns()
            assert node.gate is None,'receiver must not select a guard for a control decision'
        elif stream=='contacts':
            saved=node.inbox.pending['contacts'][17_000_000_000]
            assert saved.data['forces']==(30.,)*4
            assert before<=saved.received_ns<=time.monotonic_ns()
        else:
            assert node.command.data==(.01,0.,0.)
            assert before<=node.command.received_ns<=time.monotonic_ns()
    finally:
        node.destroy_node();peer.destroy_node();context.try_shutdown()
    assert node.ingress_worker.joined,'owned receiver must join before ROS resources are destroyed'


def test_receiver_callback_failure_is_sticky_and_worker_is_joined():
    from integrated_robot_navigation.ingress_dispatch import IngressDispatch
    from std_msgs.msg import UInt64
    context=Context();rclpy.init(context=context)
    peer=Node('failed_ingress_peer',context=context)
    def fail(msg):raise ValueError('original callback failure')
    worker=IngressDispatch(context,'failed_ingress','/',[
        ((UInt64,'/independent_ingress/failure',fail,1),{})])
    pub=peer.create_publisher(UInt64,'/independent_ingress/failure',1)
    try:
        deadline=time.monotonic()+2.
        while pub.get_subscription_count()!=1 and time.monotonic()<deadline:time.sleep(.01)
        assert pub.get_subscription_count()==1
        deadline=time.monotonic()+.2
        while worker.error is None and time.monotonic()<deadline:
            pub.publish(UInt64(data=1));time.sleep(.005)
        assert worker.error and 'original callback failure' in worker.error
        worker.thread.join(timeout=1.)
        assert not worker.thread.is_alive(),'failed receiver cannot silently resume'
        saved=worker.error
        pub.publish(UInt64(data=2));time.sleep(.025)
        assert worker.error==saved and not worker.thread.is_alive()
    finally:
        worker.close();peer.destroy_node();context.try_shutdown()
    assert worker.joined


def test_original_timesource_updates_without_model_pool_dispatch():
    from rosgraph_msgs.msg import Clock
    context=Context();rclpy.init(context=context)
    node=CrawlController(context=context,cli_args=['--ros-args','-r',
        '/clock:=/navigation/control_clock'],parameter_overrides=[
        Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
        Parameter('control_clock_mode',value='relay100')])
    peer=Node('independent_clock_peer',context=context)
    publisher=peer.create_publisher(Clock,'/navigation/control_clock',qos_profile_sensor_data)
    try:
        deadline=time.monotonic()+2.
        while publisher.get_subscription_count()!=1 and time.monotonic()<deadline:time.sleep(.01)
        assert publisher.get_subscription_count()==1,'the original TimeSource must remain unique'
        message=Clock();message.clock.sec=17;message.clock.nanosec=123
        deadline=time.monotonic()+.15
        while node.get_clock().now().nanoseconds!=17_000_000_123 and time.monotonic()<deadline:
            publisher.publish(message);time.sleep(.005)
        assert node.get_clock().now().nanoseconds==17_000_000_123, \
            'original TimeSource clock starved behind the model thread pool'
        assert peer.count_publishers('/navigation/control_clock')==1
        assert node.machine is None and not node.active
        # Exercise the public TimeSource unsubscribe/recreate lifecycle too.
        result=node.set_parameters([Parameter('use_sim_time',value=False)])
        assert all(item.successful for item in result)
        assert not node.navigation_clock_subscriptions
        result=node.set_parameters([Parameter('use_sim_time',value=True)])
        assert all(item.successful for item in result)
        assert len(node.navigation_clock_subscriptions)==1
        message.clock.sec=18
        deadline=time.monotonic()+.3
        while node.get_clock().now().nanoseconds!=18_000_000_123 and time.monotonic()<deadline:
            publisher.publish(message);time.sleep(.005)
        assert node.get_clock().now().nanoseconds==18_000_000_123
        assert publisher.get_subscription_count()==1
    finally:
        node.destroy_node();peer.destroy_node();context.try_shutdown()
    assert node.ingress_worker.joined
