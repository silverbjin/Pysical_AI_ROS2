"""Actual finishing subscription must retain its guard until the pool joins."""
from threading import Event, Thread
import time
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from std_msgs.msg import String
from integrated_robot_navigation.clock_execution import ControlClockLifecycleNode,make_control_executor


def test_relay_executor_drains_real_callback_before_destroying_its_guard():
    context=Context();rclpy.init(context=context,domain_id=166)
    node=ControlClockLifecycleNode('shutdown_owner',context=context)
    node.declare_parameter('control_clock_mode','relay100')
    node.declare_parameter('validation_mode',True)
    peer=Node('shutdown_source',context=context)
    executor=make_control_executor(node);executor.add_node(node)
    entered,release,pool_join_started,guard_destroyed=Event(),Event(),Event(),Event()
    failures=[];closer=None
    # Observe real lifetime boundaries; neither underlying operation is mocked.
    guard=executor._guard;destroy=guard.destroy
    def observe_destroy():
        guard_destroyed.set();return destroy()
    guard.destroy=observe_destroy
    pool_shutdown=executor._executor.shutdown
    def observe_join(*args,**kwargs):
        pool_join_started.set();return pool_shutdown(*args,**kwargs)
    executor._executor.shutdown=observe_join
    def callback(msg):
        entered.set()
        assert release.wait(3.),'test callback release missing'
    node.create_subscription(String,'/shutdown_boundary',callback,10)
    pub=peer.create_publisher(String,'/shutdown_boundary',10)
    def shutdown():
        try:executor.shutdown(timeout_sec=2.)
        except BaseException as error:failures.append(error)
    try:
        end=time.monotonic()+3.
        while pub.get_subscription_count()!=1 and time.monotonic()<end:executor.spin_once(timeout_sec=.01)
        assert pub.get_subscription_count()==1
        pub.publish(String(data='one actual callback'))
        while not entered.is_set() and time.monotonic()<end:executor.spin_once(timeout_sec=.01)
        assert entered.is_set()
        closer=Thread(target=shutdown);closer.start()
        assert pool_join_started.wait(1.)
        assert not guard_destroyed.is_set(),'ROS guard destroyed while a real callback still owns it'
        release.set();closer.join(timeout=2.)
        assert not closer.is_alive() and not failures
        assert guard_destroyed.is_set()
        assert all(f.exception() is None for f in executor._futures if f.done())
    finally:
        release.set()
        if closer is not None:closer.join(timeout=3.)
        else:executor.shutdown(timeout_sec=2.)
        assert closer is None or not closer.is_alive(),'test retains ROS resources until actual join'
        for future in executor._futures:
            if future.done():future.exception()  # retain/consume RED failure, never leave an unobserved task
        node.destroy_node();peer.destroy_node();context.try_shutdown()
