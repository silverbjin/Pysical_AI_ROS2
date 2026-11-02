"""Remove warning-only waitables, retain message/QoS/custom-event contracts."""
import importlib
import importlib.util
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.event_handler import SubscriptionEventCallbacks
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String


@pytest.mark.parametrize('lifecycle',[False,True])
def test_owned_nodes_keep_qos_and_complete_messages_with_fewer_warning_waitables(lifecycle):
    assert importlib.util.find_spec('integrated_robot_navigation.dispatch_node'),'bounded event policy missing'
    api=importlib.import_module('integrated_robot_navigation.dispatch_node')
    context=Context();rclpy.init(context=context,domain_id=165)
    node=(api.NavigationLifecycleNode if lifecycle else api.NavigationNode)('owned_events',context=context)
    ordinary=Node('default_events',context=context)
    executor=SingleThreadedExecutor(context=context)
    received=[];qos=QoSProfile(depth=10)
    try:
        pub=node.create_publisher(String,'/owned_events',qos)
        sub=node.create_subscription(String,'/owned_events',lambda msg:received.append(msg.data),qos)
        ordinary.create_publisher(String,'/default_events',qos)
        ordinary.create_subscription(String,'/default_events',lambda msg:None,qos)
        assert pub.qos_profile==qos and sub.qos_profile==qos
        assert not pub.event_handlers and not sub.event_handlers
        assert len(tuple(node.waitables))<len(tuple(ordinary.waitables))
        executor.add_node(node)
        deadline=time.monotonic()+3.
        while pub.get_subscription_count()!=1 and time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
        assert pub.get_subscription_count()==1
        for i in range(8):pub.publish(String(data=str(i)))
        while len(received)<8 and time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
        assert received==[str(i) for i in range(8)]
    finally:
        executor.shutdown();node.destroy_node();ordinary.destroy_node();rclpy.shutdown(context=context)


def test_explicit_matched_callback_is_preserved_and_executed():
    assert importlib.util.find_spec('integrated_robot_navigation.dispatch_node'),'bounded event policy missing'
    api=importlib.import_module('integrated_robot_navigation.dispatch_node')
    context=Context();rclpy.init(context=context,domain_id=165)
    node=api.NavigationNode('explicit_events',context=context)
    executor=SingleThreadedExecutor(context=context);matched=[]
    try:
        callbacks=SubscriptionEventCallbacks(matched=lambda event:matched.append(event.current_count))
        sub=node.create_subscription(String,'/explicit_events',lambda msg:None,10,event_callbacks=callbacks)
        assert len(sub.event_handlers)>=1
        node.create_publisher(String,'/explicit_events',10)
        executor.add_node(node);deadline=time.monotonic()+3.
        while not matched and time.monotonic()<deadline:executor.spin_once(timeout_sec=.01)
        assert 1 in matched
    finally:
        executor.shutdown();node.destroy_node();rclpy.shutdown(context=context)
