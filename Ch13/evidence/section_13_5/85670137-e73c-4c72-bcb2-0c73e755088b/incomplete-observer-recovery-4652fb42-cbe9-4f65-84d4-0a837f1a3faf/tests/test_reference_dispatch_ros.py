"""Real DDS notifications only; an inactive model never gains motor authority."""
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Time
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor
from test_execution_admission_contract import fixture
from test_g2_control_cadence_ros import controller


@pytest.mark.parametrize('arrival',['clock','ack'])
def test_original_clock_and_ack_can_wake_one_waiting_owner_without_periodic_polling(tmp_path,nav_robot_model,monkeypatch,arrival):
    ctx=Context();rclpy.init(context=ctx);calls=[];original=CrawlController._tick
    def record(node):
        calls.append((node.get_clock().now().nanoseconds,time.monotonic_ns()))
        return original(node)
    monkeypatch.setattr(CrawlController,'_tick',record)
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    node=controller(ctx,nav_robot_model,profile,expected)
    peer=Node('original_reference_notification_source',context=ctx)
    executor=make_control_executor(node);executor.add_node(node);executor.add_node(peer)
    source=peer.create_publisher(Clock,'/navigation/control_clock',10)
    ack=peer.create_publisher(JointState,'/navigation/applied_reference',1)
    for timer in node.timers:
        if timer.clock is node.get_clock():timer.cancel()  # isolate notifications from the regular timer
    def pump(seconds,stamp=None,message=None):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if stamp is not None:source.publish(Clock(clock=Time(sec=1,nanosec=stamp-10**9)))
            if message is not None:ack.publish(message)
            executor.spin_once(timeout_sec=.001);time.sleep(.001)
    try:
        stamp=1_030_000_000 if arrival=='clock' else 1_050_000_000
        pump(.1,stamp)
        assert node.get_clock().now().nanoseconds==stamp
        assert getattr(node,'reference_dispatch',None) is not None, 'applied-reference wake path missing'
        target=(.01,)*len(nav_robot_model.joint_names)
        now=time.monotonic_ns()
        with node.inbox_lock:
            node.last_control_dispatch_wall_ns=now
            node.reference_dispatch.issued(1_000_000_000,now-30_000_000)
            node.reference_dispatch.defer()
            node.reference_retry_hint=dict(values=target,issued_ros_ns=1_000_000_000,
                issued_wall_ns=now-30_000_000)
        calls.clear()
        message=JointState(name=list(nav_robot_model.joint_names),position=list(target))
        message.header.stamp=Time(sec=1,nanosec=40_000_000)
        message.header.frame_id='mujoco/pre_step'
        if arrival=='clock':
            pump(.025,message=message)
            assert not calls, 'future ACK notified control before the original clock reached it'
            pump(.035,1_050_000_000)
        else:
            pump(.02)
            assert not calls, 'no matching original ACK had arrived'
            pump(.035,message=message)
        assert len(calls)==1, 'arrival did not wake exactly one owner without the periodic timer'
        sample=node._applied_pending[1_040_000_000]
        assert sample.stamp_ns==1_040_000_000 and sample.data['position']==target
        assert not node.active and node.machine is None and node.command_publication_count==0
        assert node.reference_dispatch.snapshot()['notifications']==1
    finally:
        assert executor.shutdown(timeout_sec=2.)
        node.destroy_node();peer.destroy_node();ctx.try_shutdown()


def test_pending_native_application_emits_no_duplicate_commands_and_expires_original_lease(tmp_path,nav_robot_model):
    from test_mujoco_relay_validation_scope import relay_proof
    from test_execution_admission_contract import contract
    from test_crawl_lifecycle import CrawlRig
    from test_crawl_safety_ros import activate
    profile,_,_=relay_proof(tmp_path,nav_robot_model,'a'*64)
    ctx=Context();rclpy.init(context=ctx)
    node=controller(ctx,nav_robot_model,profile,contract('mujoco'))
    rig=CrawlRig(node,nav_robot_model,ctx)
    rig.node.destroy_publisher(rig.clock)
    rig.clock=rig.node.create_publisher(Clock,'/navigation/control_clock',10)
    echo=rig.node.create_publisher(JointState,'/navigation/applied_reference',1)
    try:
        rig.pump(.3);activate(rig);rig.ready=True
        rig.mode_name='CRAWL';rig.value=.001
        # Planning is not an issued command. Start the lease check only once
        # this real owner actually submitted its first changed reference.
        deadline=time.monotonic()+3.
        while not node.applied_credit.events and time.monotonic()<deadline:
            rig.pump(.02)
        assert node.applied_credit.events,(node.machine.state,node.machine.reason,
            node.machine.phase,node.admission,node.reference_dispatch.snapshot())
        rig.pump(.3)
        assert 'unconfirmed' in node.stop_reason,node.stop_reason
        assert node.first_stop is not None and node.applied_credit.last_ack is None
        submitted=[row for row in node.applied_credit.events if row['event']=='submitted']
        assert len(submitted)==1, 'unconfirmed command was replaced or renewed'
        issue=submitted[0]['issued_wall_ns'];stop=node.first_stop['wall_ns']
        assert max(stop-issue,node.first_stop['ros_ns']-submitted[0]['issued_ros_ns'])>200_000_000
        rows=[row for row in node.command_publications if issue<=row['publish_started_ns']<stop]
        assert len(rows)==1, 'identical pending reference was needlessly republished'
        assert not node.reference_dispatch.waiting and not rig.crawl_states[-1].ready
        reason=node.stop_reason;rig.pump(.15)
        assert node.stop_reason==reason and node.applied_credit.last_ack is None
    finally:
        rig.node.destroy_publisher(echo);rig.close();ctx.try_shutdown()
