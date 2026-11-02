"""Explicit G2 parameter scope plus a real ROS mode request; no engine proof."""
import importlib
import json
import pytest
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter
from test_execution_admission_contract import fixture
from test_motion_guard_ros import Rig


@pytest.mark.parametrize('validation,g2,payload',[(False,True,'valid'),(True,True,''),(True,False,'valid')])
@pytest.mark.parametrize('role',['motion_guard','crawl_controller'])
def test_g2_context_cannot_enter_default_or_incomplete_scope(tmp_path,nav_robot_model,role,validation,g2,payload):
    module=importlib.import_module('integrated_robot_navigation.'+role)
    kind=module.MotionGuardNode if role=='motion_guard' else module.CrawlController
    profile,expected=fixture(tmp_path,nav_robot_model,'gazebo')
    context=Context();rclpy.init(context=context);node=None
    try:
        with pytest.raises(ValueError,match='G2|scope|profile'):
            node=kind(nav_robot_model,profile,'gazebo',context=context,parameter_overrides=[
                Parameter('validation_mode',value=validation),Parameter('g2_validation_mode',value=g2),
                Parameter('native_execution_profile',value=json.dumps(expected) if payload else '')])
    finally:
        if node is not None:node.destroy_node()
        context.try_shutdown()


def test_actual_g2_guard_service_needs_matched_prepared_g1_profile(tmp_path,nav_robot_model):
    module=importlib.import_module('integrated_robot_navigation.motion_guard')
    profile,expected=fixture(tmp_path,nav_robot_model,'gazebo')
    context=Context();rclpy.init(context=context);node=None;rig=None
    try:
        node=module.MotionGuardNode(nav_robot_model,profile,'gazebo',context=context,parameter_overrides=[
            Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
            Parameter('g2_validation_mode',value=True),Parameter('native_execution_profile',value=json.dumps(expected))])
        rig=Rig(node,nav_robot_model,context);rig.pump(.5)
        assert rig.mode('CRAWL').accepted,'explicit approved G2 still follows the G1-only rejection path'
    finally:
        if rig is not None:rig.close()
        elif node is not None:node.destroy_node()
        context.try_shutdown()
