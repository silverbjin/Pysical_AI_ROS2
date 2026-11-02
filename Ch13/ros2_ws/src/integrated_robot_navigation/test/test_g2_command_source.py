"""Actual DDS command fixture only; it cannot establish native movement."""
import importlib.util
import math
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Twist
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_navigation.carry_profile import default_limits


def kind():
    assert importlib.util.find_spec('integrated_robot_navigation.g2_command_source'),'owned G2 command source missing'
    from integrated_robot_navigation.g2_command_source import G2CommandSource
    return G2CommandSource


def test_real_wire_ramp_is_bounded_and_fault_blocks_all_future_targets():
    cls=kind();context=Context();rclpy.init(context=context,domain_id=169)
    limits=default_limits();source=cls(limits,context=context);peer=Node('g2_source_peer',context=context)
    executor=SingleThreadedExecutor(context=context);executor.add_node(source);executor.add_node(peer)
    raw=[];smoothed=[]
    peer.create_subscription(Twist,'/navigation/cmd_vel_raw',raw.append,100)
    peer.create_subscription(Twist,'/navigation/cmd_vel_smoothed',smoothed.append,100)
    fault=peer.create_publisher(MotionState,'/navigation/guard_state',10)
    def pump(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:executor.spin_once(timeout_sec=.005)
    try:
        pump(.15);source.set_target(.01,.03);pump(.8)
        assert len(raw)>=10 and len(smoothed)>=10
        assert all(0<=m.linear.x<=.01 and 0<=m.angular.z<=.03 for m in smoothed)
        assert all(m.linear.y==m.linear.z==m.angular.x==m.angular.y==0 for m in raw+smoothed)
        history=source.report()['publications']
        for previous,current in zip(history,history[1:]):
            dt=(current['wall_ns']-previous['wall_ns'])/1e9
            assert dt>=.02
            assert abs(current['smoothed'][0]-previous['smoothed'][0])<=limits['max_accel_x']*dt+1e-12
            assert abs(current['smoothed'][1]-previous['smoothed'][1])<=limits['max_accel_wz']*dt+1e-12
        fault.publish(MotionState(state='FAULT',fault_reason='unit fault'));pump(.1)
        assert source.report()['closing'] is True
        assert smoothed[-1].linear.x==smoothed[-1].angular.z==0
        count=len(smoothed);pump(.08);assert len(smoothed)==count
        with pytest.raises(RuntimeError):source.set_target(.005,0.)
    finally:
        source.stop();executor.shutdown(timeout_sec=2.)
        source.destroy_node();peer.destroy_node();context.try_shutdown()


@pytest.mark.parametrize('vx,wz',[(math.nan,0.),(.01001,0.),(0.,.03001)])
def test_invalid_target_closes_source_without_sending_it(vx,wz):
    cls=kind();context=Context();rclpy.init(context=context,domain_id=169)
    source=cls(default_limits(),context=context)
    try:
        with pytest.raises(ValueError):source.set_target(vx,wz)
        assert source.report()['closing'] is True
        with pytest.raises(RuntimeError):source.set_target(0.,0.)
    finally:source.destroy_node();context.try_shutdown()
