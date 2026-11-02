"""A delayed proof identity check must not stall the original ROS clock.

Real DDS and selected executor, deliberately delayed filesystem boundary;
this is transport isolation proof, not native gait evidence.
"""
import json
import threading
import time

import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.motion_guard import MotionGuardNode
from test_execution_admission_contract import fixture
from test_motion_guard_ros import Rig


def test_g2_slow_admission_preserves_clock_and_defers_motion_grant(tmp_path,nav_robot_model):
    profile,expected=fixture(tmp_path,nav_robot_model,'gazebo')
    context=Context();rclpy.init(context=context)
    guard=MotionGuardNode(nav_robot_model,profile,'gazebo',context=context,parameter_overrides=[
        Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
        Parameter('g2_validation_mode',value=True),Parameter('native_execution_profile',value=json.dumps(expected))])
    rig=Rig(guard,nav_robot_model,context)
    entered,release,stopping=threading.Event(),threading.Event(),threading.Event()
    thread=None
    try:
        rig.pump(.4)
        assert rig.mode('STAND').accepted
        original=guard.prepared_admission.check
        def delayed(*args,**kwargs):
            entered.set()
            assert release.wait(2.),'test check release deadline'
            return original(*args,**kwargs)
        guard.prepared_admission.check=delayed
        def spin():
            while not stopping.is_set():rig.executor.spin_once(timeout_sec=.005)
        thread=threading.Thread(target=spin);thread.start()
        future=rig.client.call_async(SetMode.Request(mode='CRAWL'))
        assert entered.wait(1.)
        before=guard.get_clock().now().nanoseconds
        for index in range(1,26):
            stamp=before+index*10_000_000
            rig.clock.publish(Clock(clock=Time(sec=stamp//1_000_000_000,nanosec=stamp%1_000_000_000)))
            time.sleep(.01)
        assert guard.core.mode=='STAND' and not future.done(), 'pending proof cannot grant motion'
        assert guard.get_clock().now().nanoseconds>=before+200_000_000, \
            'mode callback blocked original clock dispatch for the entire safety age budget'
        release.set()
        deadline=time.monotonic()+1.
        while not future.done() and time.monotonic()<deadline:time.sleep(.005)
        assert future.done() and future.result().accepted
    finally:
        release.set();stopping.set()
        if thread is not None:thread.join(2.);assert not thread.is_alive()
        rig.close();context.try_shutdown()
