"""Explicit validation math scopes; arithmetic is no command permission."""
import pytest
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter
from integrated_robot_navigation.crawl_controller import CrawlController
from test_execution_admission_contract import fixture
from test_g2_control_cadence_ros import controller


@pytest.mark.parametrize('scope',['g2_relay','g1_relay','native','gazebo_relay'])
def test_mass_kernel_is_owned_by_explicit_configuration_and_closed_after_model(tmp_path,nav_robot_model,scope):
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    ctx=Context();rclpy.init(context=ctx)
    if scope in ('g2_relay','g1_relay'):
        node=controller(ctx,nav_robot_model,profile,expected,g2=scope=='g2_relay')
    else:
        relay=scope=='gazebo_relay'
        node=CrawlController(nav_robot_model,profile,'gazebo' if relay else 'mujoco',context=ctx,
            cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'] if relay else [],
            parameter_overrides=[Parameter('validation_mode',value=relay),
                Parameter('control_clock_mode',value='relay100' if relay else 'native')])
    core=geometry=None
    try:
        node.trigger_configure()
        assert node.machine is not None
        core=getattr(node,'mass_evaluator',None)
        if scope in ('g2_relay','gazebo_relay'):
            assert core is not None, 'G2 still dispatches many small matrix operations across Python'
            assert node.machine._mass_evaluator is core
            assert core.provenance['model_sha256']==nav_robot_model.model_sha256
        else:assert core is None
        geometry=getattr(node.machine,'_kinematics_evaluator',None)
        if scope=='gazebo_relay':
            from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
            assert isinstance(geometry,NativeReferenceEnvelope)
        else:assert geometry is None
        assert node.command_publication_count==0 and not node.active
    finally:
        node.destroy_node();ctx.try_shutdown()
    if core is not None:assert not core._finalize.alive
    if geometry is not None:assert not geometry._finalize.alive
