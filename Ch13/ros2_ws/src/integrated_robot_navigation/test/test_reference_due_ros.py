"""A one-shot wall deadline need not wait for another Clock/ACK message."""
import time
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from builtin_interfaces.msg import Time
from rosgraph_msgs.msg import Clock
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor
from test_execution_admission_contract import fixture
from test_g2_control_cadence_ros import controller
from types import SimpleNamespace


def test_confirmed_reference_wakes_at_wall_due_with_only_positive_original_ros_progress(tmp_path,nav_robot_model,monkeypatch):
    ctx=Context();rclpy.init(context=ctx);calls=[];original=CrawlController._tick
    def record(node):
        calls.append((node.get_clock().now().nanoseconds,time.monotonic_ns()))
        return original(node)
    monkeypatch.setattr(CrawlController,'_tick',record)
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    node=controller(ctx,nav_robot_model,profile,expected)
    peer=Node('reference_due_source',context=ctx);executor=make_control_executor(node)
    executor.add_node(node);executor.add_node(peer)
    source=peer.create_publisher(Clock,'/navigation/control_clock',10)
    for timer in node.timers:
        if timer.clock is node.get_clock():timer.cancel()
    try:
        deadline=time.monotonic()+.1
        while time.monotonic()<deadline:
            source.publish(Clock(clock=Time(sec=1,nanosec=18_000_000)))
            executor.spin_once(timeout_sec=.001);time.sleep(.001)
        assert node.get_clock().now().nanoseconds==1_018_000_000
        assert callable(getattr(node,'_schedule_reference_due',None)), 'owned wall-due notification missing'
        issued=time.monotonic_ns()
        with node.inbox_lock:
            node.last_control_dispatch_wall_ns=issued
            node.reference_dispatch.issued(1_000_000_000,issued)
            node.reference_dispatch.defer();node.reference_retry_hint=None  # already confirmed
        calls.clear();node._schedule_reference_due()
        deadline=time.monotonic()+.12
        while time.monotonic()<deadline:
            executor.spin_once(timeout_sec=.001);time.sleep(.001)
        assert len(calls)==1, 'control waited for another source message or notified more than once'
        assert calls[0][1]-issued>=20_000_000
        assert calls[0][0]==1_018_000_000, 'original ROS clock was extrapolated or replaced'
        assert node.reference_due_timer.is_canceled()
        assert not node.active and node.command_publication_count==0
    finally:
        assert executor.shutdown(timeout_sec=2.)
        node.destroy_node();peer.destroy_node();ctx.try_shutdown()


def test_early_ros_timer_cannot_occupy_reserved_wall_control_period(tmp_path,nav_robot_model,monkeypatch):
    """Real TimeSource/timers/executor; synthetic 15ms owner cost, no motors.

    A coarse source-clock packet can make the ROS timer ready before the
    reserved wall period. It must not perform an extra full model calculation.
    The actual due callback must still run with the original positive clock.
    """
    ctx=Context();rclpy.init(context=ctx);calls=[]
    def cost(node):
        calls.append((node.get_clock().now().nanoseconds,time.monotonic_ns()))
        time.sleep(.015)
    monkeypatch.setattr(CrawlController,'_tick',cost)
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    node=controller(ctx,nav_robot_model,profile,expected)
    peer=Node('early_reference_timer_source',context=ctx);executor=make_control_executor(node)
    executor.add_node(node);executor.add_node(peer)
    source=peer.create_publisher(Clock,'/navigation/control_clock',10)
    def pump(duration,stamp=None):
        end=time.monotonic()+duration
        while time.monotonic()<end:
            if stamp is not None:source.publish(Clock(clock=Time(sec=1,nanosec=stamp)))
            executor.spin_once(timeout_sec=.001);time.sleep(.001)
    try:
        pump(.15,0)
        calls.clear();issued=time.monotonic_ns()
        with node.inbox_lock:
            node.active=True;node._credit_motion=True
            node.machine=SimpleNamespace(state='CRAWL',stopping=False)
            node.last_control_dispatch_wall_ns=issued
            node.reference_dispatch.issued(1_000_000_000,issued)
            node.reference_dispatch.defer();node.reference_retry_hint=None
        node._schedule_reference_due()
        pump(.12,22_000_000)
        assert len(calls)==1, 'early periodic callback competed with the reserved owner decision'
        assert calls[0][1]-issued>=20_000_000, 'full computation started before the reserved wall period'
        assert calls[0][0]==1_022_000_000
        assert node.command_publication_count==0
    finally:
        assert executor.shutdown(timeout_sec=2.)
        node.destroy_node();peer.destroy_node();ctx.try_shutdown()
