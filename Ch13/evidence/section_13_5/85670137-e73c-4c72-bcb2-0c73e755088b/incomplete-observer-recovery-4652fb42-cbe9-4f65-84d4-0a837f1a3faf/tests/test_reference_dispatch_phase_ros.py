"""The control period includes computation; it is not a post-work sleep.

Actual ROS owner/command submission with deliberately slow arithmetic fixture.
No native physics or gait acceptance is claimed.
"""
import time
import rclpy
from rclpy.context import Context
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from test_mujoco_relay_validation_scope import relay_proof
from test_execution_admission_contract import contract
from test_g2_control_cadence_ros import controller
from test_crawl_lifecycle import CrawlRig
from test_crawl_safety_ros import activate


def test_next_reference_can_begin_20ms_after_decision_even_when_previous_computation_took_time(tmp_path,nav_robot_model):
    profile,_,_=relay_proof(tmp_path,nav_robot_model,'a'*64)
    ctx=Context();rclpy.init(context=ctx)
    node=controller(ctx,nav_robot_model,profile,contract('mujoco'))
    rig=CrawlRig(node,nav_robot_model,ctx)
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    echo=rig.node.create_publisher(JointState,'/navigation/applied_reference',1)
    try:
        rig.pump(.3);activate(rig);rig.ready=True
        original=node.machine.advance
        def controlled_computation(*args,**kwargs):
            result=original(*args,**kwargs)
            time.sleep(.015)
            return result
        node.machine.advance=controlled_computation
        rig.mode_name='CRAWL';rig.value=.001
        deadline=time.monotonic()+3.
        while not node.applied_credit.events and time.monotonic()<deadline:rig.pump(.02)
        with node.lock:
            assert node.applied_credit.events,'first real submission was not reached'
            row=node.command_publications[-1]
            assert row['publish_started_ns']-row['decision_wall_ns']>=15_000_000
            assert node.reference_dispatch.allowed(row['decision_ros_ns']+20_000_000,
                row['decision_wall_ns']+20_000_000), '20ms period was restarted after computation'
            pending=node.applied_credit.pending
            assert pending is not None and pending['issued_wall_ns']==row['publish_started_ns'], \
                'application deadline must still begin at actual publication'
    finally:
        rig.node.destroy_publisher(echo);rig.close();ctx.try_shutdown()
