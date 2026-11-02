"""Real DDS applied-reference inbox; synthetic producer is not engine proof."""
import json
import time
import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, ReliabilityPolicy
from sensor_msgs.msg import JointState
from integrated_robot_navigation.crawl_controller import CrawlController
from test_execution_admission_contract import fixture
from test_crawl_lifecycle import CrawlRig
from test_crawl_safety_ros import activate


@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_only_explicit_mujoco_g2_owns_an_applied_reference_inbox(tmp_path,nav_robot_model,engine):
    profile,execution=fixture(tmp_path,nav_robot_model,engine)
    ctx=Context();rclpy.init(context=ctx);node=None
    try:
        node=CrawlController(nav_robot_model,profile,engine,context=ctx,parameter_overrides=[
            Parameter('validation_mode',value=True),Parameter('g2_validation_mode',value=True),
            Parameter('native_execution_profile',value=json.dumps(execution))])
        node.trigger_configure()
        assert hasattr(node,'applied_credit'),'actual leg owner lacks application credit binding'
        assert (node.applied_credit is not None)==(engine=='mujoco')
        if engine=='mujoco':
            endpoints=node.get_subscriptions_info_by_topic('/navigation/applied_reference')
            assert len(endpoints)==1
            assert endpoints[0].qos_profile.reliability==ReliabilityPolicy.RELIABLE, \
                'one-shot application events need reliable delivery, not a lossy sensor stream'
    finally:
        if node is not None:node.destroy_node()
        ctx.try_shutdown()


def test_actual_dds_echo_preserves_first_receipt_and_sole_publisher(tmp_path,nav_robot_model):
    profile,execution=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx);owner=source=executor=None
    try:
        owner=CrawlController(nav_robot_model,profile,'mujoco',context=ctx,parameter_overrides=[
            Parameter('validation_mode',value=True),Parameter('g2_validation_mode',value=True),
            Parameter('native_execution_profile',value=json.dumps(execution))])
        owner.trigger_configure()
        assert hasattr(owner,'applied_credit'),'applied DDS owner missing'
        credit=owner.applied_credit
        source=Node('synthetic_pre_step_echo',context=ctx)
        publisher=source.create_publisher(JointState,'/navigation/applied_reference',1)
        executor=SingleThreadedExecutor(context=ctx);executor.add_node(owner);executor.add_node(source)
        end=time.monotonic()+1.
        while publisher.get_subscription_count()<1 and time.monotonic()<end:executor.spin_once(timeout_sec=.01)
        credit.prime((0.,)*12)
        stamp=owner.get_clock().now().nanoseconds;wall=time.monotonic_ns()
        credit.submitted((.001,)*12,stamp,wall)
        message=JointState();message.header.stamp=owner.get_clock().now().to_msg()
        message.header.frame_id='mujoco/pre_step';message.name=list(nav_robot_model.joint_names)
        message.position=[.001]*12
        end=time.monotonic()+.15
        while credit.snapshot()['last_ack'] is None and time.monotonic()<end:
            publisher.publish(message);executor.spin_once(timeout_sec=.005)
            owner._reference_permitted((.001,0.,0.),owner.get_clock().now().nanoseconds,time.monotonic_ns())
        ack=credit.snapshot()['last_ack'];assert ack is not None
        first=ack['received_ns'];assert first>=wall
        cutoff_ros=owner.get_clock().now().nanoseconds;cutoff_wall=time.monotonic_ns()
        diagnostic=owner._application_snapshot(cutoff_ros,cutoff_wall)
        assert diagnostic['cutoff_ros_ns']==cutoff_ros and diagnostic['cutoff_wall_ns']==cutoff_wall
        assert diagnostic['credit']['last_ack']['received_ns']==first
        assert any(row['received_ns']==first for row in diagnostic['credit']['received_samples'])
        assert 'pending_ingress' in diagnostic
        diagnostic['credit']['last_ack']['received_ns']=0
        assert credit.snapshot()['last_ack']['received_ns']==first,'diagnostic mutated the owner'
        extra=source.create_publisher(JointState,'/navigation/applied_reference',1)
        end=time.monotonic()+.5
        while owner.count_publishers('/navigation/applied_reference')<2 and time.monotonic()<end:
            executor.spin_once(timeout_sec=.01)
        with pytest.raises(ValueError,match='owner'):
            owner._reference_permitted((.001,0.,0.),owner.get_clock().now().nanoseconds,time.monotonic_ns())
        assert credit.snapshot()['last_ack']['received_ns']==first
        source.destroy_publisher(extra)
    finally:
        if executor is not None:executor.shutdown()
        if source is not None:source.destroy_node()
        if owner is not None:owner.destroy_node()
        ctx.try_shutdown()


def test_actual_owner_keeps_safety_ticks_and_stops_when_application_is_unconfirmed(tmp_path,nav_robot_model):
    profile,execution=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx);owner=rig=None
    try:
        owner=CrawlController(nav_robot_model,profile,'mujoco',context=ctx,parameter_overrides=[
            Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
            Parameter('g2_validation_mode',value=True),Parameter('native_execution_profile',value=json.dumps(execution))])
        rig=CrawlRig(owner,nav_robot_model,ctx)
        # Publisher presence is not evidence that any command was applied.
        echo=rig.node.create_publisher(JointState,'/navigation/applied_reference',1)
        rig.pump(.3);activate(rig);rig.ready=True
        original=owner.machine.advance;calls=[]
        def observed_advance(*args,**kwargs):
            calls.append((args[2],args[3],kwargs.get('reference_permitted',True)))
            return original(*args,**kwargs)
        owner.machine.advance=observed_advance
        rig.mode_name='CRAWL';rig.value=.001;rig.pump(.8)
        assert any(not row[2] for row in calls),'pending command did not hold references'
        assert len(calls)>10 and calls[-1][0]>calls[0][0] and calls[-1][1]>calls[0][1]
        assert 'unconfirmed' in owner.stop_reason,owner.stop_reason
        assert owner.first_stop is not None and not rig.crawl_states[-1].ready
        reason=owner.stop_reason;rig.pump(.15)
        assert owner.stop_reason==reason,'continued input reactivated an application fault'
        assert owner.applied_credit.snapshot()['last_ack'] is None
        rig.node.destroy_publisher(echo)
    finally:
        if rig is not None:rig.close()
        elif owner is not None:owner.destroy_node()
        ctx.try_shutdown()
