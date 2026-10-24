"""Installed upstream event loop: original clock/header, serial callbacks, RPC."""
import time
import rclpy
import pytest
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PointStamped
from rosgraph_msgs.msg import Clock as ClockMessage
from builtin_interfaces.msg import Time
from std_srvs.srv import Trigger
from integrated_robot_navigation import dispatch_node as api
from integrated_robot_navigation.clock_execution import ControlClockLifecycleNode,make_control_executor
from integrated_robot_runtime.common import DrainingExecutor


def test_actual_events_executor_preserves_capture_clock_steady_timer_and_service():
    assert hasattr(api,'make_navigation_executor'),'upstream event factory missing'
    context=Context();rclpy.init(context=context,domain_id=167)
    node=api.NavigationNode('events_owner',context=context,parameter_overrides=[Parameter('use_sim_time',value=True)])
    peer=Node('events_source',context=context);executor=api.make_navigation_executor(node)
    received=[];pulses=[]
    try:
        assert type(executor).__name__=='EventsExecutor' and executor.context is node.context
        executor.add_node(node);executor.add_node(peer)
        clock=peer.create_publisher(ClockMessage,'/clock',10)
        publisher=peer.create_publisher(PointStamped,'/events_capture',10)
        node.create_subscription(PointStamped,'/events_capture',received.append,10)
        node.create_timer(.02,lambda:pulses.append(time.monotonic()),clock=Clock(clock_type=ClockType.STEADY_TIME))
        node.create_service(Trigger,'/events_rpc',lambda req,res:Trigger.Response(success=True,message='actual RPC'))
        client=peer.create_client(Trigger,'/events_rpc')
        until=time.monotonic()+3.
        while publisher.get_subscription_count()!=1 and time.monotonic()<until:executor.spin_once(timeout_sec=.01)
        assert publisher.get_subscription_count()==1 and client.wait_for_service(timeout_sec=1.)
        clock.publish(ClockMessage(clock=Time(sec=7,nanosec=250000000)))
        for i in range(8):
            msg=PointStamped();msg.header.frame_id='capture_optical';msg.header.stamp=Time(sec=6,nanosec=i)
            msg.point.x=float(i);publisher.publish(msg)
        future=client.call_async(Trigger.Request())
        while (len(received)<8 or not future.done() or len(pulses)<4) and time.monotonic()<until:
            executor.spin_once(timeout_sec=.01)
        assert [m.point.x for m in received]==list(map(float,range(8)))
        assert [(m.header.frame_id,m.header.stamp.sec,m.header.stamp.nanosec) for m in received]==[
            ('capture_optical',6,i) for i in range(8)]
        assert node.get_clock().now().nanoseconds==7_250_000_000
        assert len(pulses)>=4 and future.done() and future.result().success
    finally:
        executor.shutdown(timeout_sec=2.);node.destroy_node();peer.destroy_node();context.try_shutdown()


def test_parallel_crawl_is_excluded_and_retains_its_draining_two_worker_executor():
    assert hasattr(api,'make_navigation_executor'),'upstream event factory missing'
    context=Context();rclpy.init(context=context,domain_id=167)
    node=ControlClockLifecycleNode('parallel_crawl',context=context)
    node.declare_parameter('control_clock_mode','relay100');node.declare_parameter('validation_mode',True)
    executor=None
    try:
        with pytest.raises(ValueError,match='ordinary'):api.make_navigation_executor(node)
        executor=make_control_executor(node)
        assert isinstance(executor,DrainingExecutor)
    finally:
        if executor is not None:executor.shutdown(timeout_sec=2.)
        node.destroy_node();context.try_shutdown()


def test_actual_message_info_callback_receives_original_dds_metadata_and_capture():
    context=Context();rclpy.init(context=context,domain_id=167)
    node=api.NavigationNode('info_owner',context=context)
    peer=Node('info_source',context=context);executor=api.make_navigation_executor(node);received=[]
    def receive(msg,info):received.append((msg,info))
    try:
        executor.add_node(node);executor.add_node(peer)
        node.create_subscription(PointStamped,'/events_original_info',receive,10)
        publisher=peer.create_publisher(PointStamped,'/events_original_info',10)
        until=time.monotonic()+3.
        while publisher.get_subscription_count()!=1 and time.monotonic()<until:executor.spin_once(timeout_sec=.01)
        assert publisher.get_subscription_count()==1
        msg=PointStamped();msg.header.frame_id='original';msg.header.stamp=Time(sec=3,nanosec=42)
        publisher.publish(msg)
        while not received and time.monotonic()<until:executor.spin_once(timeout_sec=.01)
        assert len(received)==1
        actual,info=received[0]
        assert (actual.header.frame_id,actual.header.stamp.sec,actual.header.stamp.nanosec)==('original',3,42)
        assert info['source_timestamp']>0 and info['received_timestamp']>0
    finally:
        executor.shutdown(timeout_sec=2.);node.destroy_node();peer.destroy_node();context.try_shutdown()
