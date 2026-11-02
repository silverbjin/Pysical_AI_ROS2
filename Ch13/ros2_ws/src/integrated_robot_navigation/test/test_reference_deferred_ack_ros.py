"""A held owner decision must not lose the subsequent native ACK wake."""
import time
import rclpy
from rclpy.context import Context
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Time
from lifecycle_msgs.msg import Transition
from integrated_robot_navigation.crawl_controller import CrawlController
from test_g2_control_cadence_ros import controller
from test_mujoco_relay_validation_scope import relay_proof
from test_execution_admission_contract import contract
from test_crawl_lifecycle import CrawlRig


def test_ack_after_held_decision_wakes_owner_without_another_periodic_tick(tmp_path,nav_robot_model,monkeypatch):
    original_configure=CrawlController.on_configure
    def loaded_configure(node,state):
        result=original_configure(node,state)
        time.sleep(.25)  # Reproduce the observed gap; test source only.
        return result
    monkeypatch.setattr(CrawlController,'on_configure',loaded_configure)
    held=[];original=CrawlController._tick
    def observe(node):
        before=node.command_publication_count
        result=original(node)
        if (node.active and node._credit_motion and node.machine.state=='CRAWL'
                and not node.machine.stopping and node.applied_credit.pending is not None
                and before==node.command_publication_count):
            held.append(node.reference_dispatch.snapshot())
        return result
    monkeypatch.setattr(CrawlController,'_tick',observe)
    profile,_,_=relay_proof(tmp_path,nav_robot_model,'a'*64)
    ctx=Context();rclpy.init(context=ctx)
    node=controller(ctx,nav_robot_model,profile,contract('mujoco'))
    rig=CrawlRig(node,nav_robot_model,ctx)
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    echo=rig.node.create_publisher(JointState,'/navigation/applied_reference',1)
    try:
        rig.pump(.3)
        assert rig.transition(Transition.TRANSITION_CONFIGURE)
        # Configuration may outlast the unchanged 200ms input lease. Publish
        # NEW test feedback before the sole activation request; do not retry a
        # refused activation or refresh the stamp on an old received message.
        rig.pump(.06)
        assert rig.transition(Transition.TRANSITION_ACTIVATE)
        rig.pump(.1);rig.ready=True
        rig.mode_name='CRAWL';rig.value=.001
        deadline=time.monotonic()+3.
        while not held and time.monotonic()<deadline:rig.pump(.02)
        assert held,(node.machine.state,node.stop_reason,node.applied_credit.snapshot())
        assert held[0]['waiting'],'held decision cancelled the only ACK wake reservation'
        pending=node.applied_credit.pending
        assert pending is not None and not node.stop_reason
        before=node.command_publication_count
        for timer in node.timers:
            if timer.clock is node.get_clock():timer.cancel()
        stamp=node.get_clock().now().nanoseconds
        message=JointState(name=list(nav_robot_model.joint_names),position=list(pending['values']))
        message.header.frame_id='mujoco/pre_step'
        message.header.stamp=Time(sec=stamp//10**9,nanosec=stamp%10**9)
        echo.publish(message);rig.pump(.06)
        assert node.applied_credit.last_ack is not None
        assert node.command_publication_count>before,'late ACK still waited for a cancelled periodic timer'
        assert node.applied_credit.last_ack['stamp_ns']==stamp
        assert not node.stop_reason
    finally:
        rig.node.destroy_publisher(echo);rig.close();ctx.try_shutdown()
