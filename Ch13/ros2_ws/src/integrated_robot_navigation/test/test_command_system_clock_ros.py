"""Controlled metadata rollback, no OS clock edits and no physical admission.

Real f4157cd3 shows a 2.166639s SYSTEM backstep while ROS/monotonic progress
and command publications continue. Actual local DDS supports publication IDs.
"""
from types import SimpleNamespace
import pytest
import rclpy
from rclpy.context import Context
from rclpy.lifecycle import TransitionCallbackReturn
from geometry_msgs.msg import Twist
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.carry_profile import prepare_profile
from integrated_robot_navigation.motion_guard import MotionGuardNode
from integrated_robot_navigation.crawl_controller import CrawlController
from guard_fixture import CARRY


def receiver(role,model,context):
    profile=prepare_profile(model,CARRY)
    if role=='final':
        node=CrawlController(model,profile,'mujoco',context=context)
        return node,node.cutoff_system,lambda msg,info:node._command(msg,info),lambda:node.command
    node=MotionGuardNode(model,profile,'mujoco',context=context)
    return node,node.reset_system,lambda msg,info:node._command(role,msg,info),lambda:node.commands[role]


@pytest.mark.parametrize('role',['raw','smoothed','final'])
@pytest.mark.parametrize('mapping',[True,False])
def test_new_dds_publication_survives_system_backstep_without_renewing_duplicate_or_old_epoch(nav_robot_model,role,mapping):
    context=Context();rclpy.init(context=context);node=None
    try:
        node,cutoff,deliver,selected=receiver(role,nav_robot_model,context)
        def info(source,sequence):
            value=dict(source_timestamp=source,publication_sequence_number=sequence)
            return value if mapping else SimpleNamespace(**value)
        first=Twist();first.linear.x=.004;deliver(first,info(cutoff+3_000_000_000,1))
        second=Twist();second.linear.x=.008;deliver(second,info(cutoff+1_000_000_000,2))
        assert selected().data[0]==.008, 'new publication was discarded because SYSTEM time moved backward'
        assert selected().sequence==cutoff+1_000_000_000, 'original source metadata was silently retagged'
        receipt=selected().received_ns
        duplicate=Twist();duplicate.linear.x=.009;deliver(duplicate,info(cutoff+4_000_000_000,2))
        assert selected().data[0]==.008 and selected().received_ns==receipt
        deliver(duplicate,info(cutoff-1,3))
        assert selected().data[0]==.008 and selected().received_ns==receipt
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()


def test_guard_does_not_clear_an_ambiguous_generation_after_system_backstep(nav_robot_model):
    context=Context();rclpy.init(context=context);node=None
    try:
        node,cutoff,deliver,_=receiver('raw',nav_robot_model,context)
        for source,sequence in ((cutoff+3_000_000_000,1),(cutoff+1_000_000_000,2)):
            deliver(Twist(),dict(source_timestamp=source,publication_sequence_number=sequence))
        generation=node.core.generation
        response=node._mode(SetMode.Request(mode='RESET'),SetMode.Response())
        assert response.accepted is False and 'restart' in response.message
        assert node.core.generation==generation
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()


@pytest.mark.parametrize('role',['raw','smoothed','final'])
def test_missing_publication_identity_is_not_replaced_by_system_order(nav_robot_model,role):
    context=Context();rclpy.init(context=context);node=None
    try:
        node,cutoff,deliver,selected=receiver(role,nav_robot_model,context)
        deliver(Twist(),dict(source_timestamp=cutoff+1))
        assert selected() is None, 'unsupported DDS identity must remain fail-closed'
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()


def test_final_command_snapshot_keeps_original_receipt_and_both_age_limits(nav_robot_model):
    from integrated_robot_navigation.samples import sample_valid
    context=Context();rclpy.init(context=context);node=None
    try:
        node,cutoff,deliver,selected=receiver('final',nav_robot_model,context)
        node.gate=SimpleNamespace(generation=0)
        deliver(Twist(),dict(source_timestamp=cutoff+1,publication_sequence_number=1))
        first=selected()
        later=Twist();later.linear.x=.008
        deliver(later,dict(source_timestamp=cutoff+2,publication_sequence_number=2))
        assert selected() is not first
        snapshot=node._command_snapshot(first.stamp_ns,first.received_ns)
        assert snapshot is first
        assert sample_valid(snapshot,first.stamp_ns+200_000_000,
                            first.received_ns+200_000_000,0,max_age_ns=200_000_000)[0]
        assert sample_valid(snapshot,first.stamp_ns+200_000_001,
                            first.received_ns,0,max_age_ns=200_000_000)==(False,'ros_age')
        assert sample_valid(snapshot,first.stamp_ns,
                            first.received_ns+200_000_001,0,max_age_ns=200_000_000)==(False,'wall_age')
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()


def test_crawl_cannot_activate_a_new_epoch_after_detected_system_backstep(nav_robot_model,monkeypatch):
    context=Context();rclpy.init(context=context);node=None
    try:
        node,cutoff,deliver,selected=receiver('final',nav_robot_model,context)
        for source,sequence in ((cutoff+3_000_000_000,1),(cutoff+1_000_000_000,2)):
            deliver(Twist(),dict(source_timestamp=source,publication_sequence_number=sequence))
        command=selected();generation=node.generation
        def forbidden_selection(*args,**kwargs):
            raise AssertionError('a clock-ambiguous receiver must not start selecting a new epoch')
        monkeypatch.setattr(node,'_select_gate',forbidden_selection)
        assert node.on_activate(None)==TransitionCallbackReturn.FAILURE
        assert node.generation==generation and selected() is command
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()
