"""Configuration selects G1 return explicitly; it grants no motion permission."""
import pytest
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter

from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.gait import CrawlMachine
from gait_fixture import IdealFeedback
from test_execution_admission_contract import fixture
from test_g2_control_cadence_ros import controller


@pytest.mark.parametrize('scope',['g2_relay','g1_relay','native','gazebo_relay'])
def test_configured_owner_preserves_mujoco_loaded_return_and_selects_gazebo_preload(tmp_path,nav_robot_model,scope):
    profile,expected=fixture(tmp_path,nav_robot_model,'mujoco')
    context=Context();rclpy.init(context=context)
    if scope in ('g2_relay','g1_relay'):
        node=controller(context,nav_robot_model,profile,expected,g2=scope=='g2_relay')
    else:
        relay=scope=='gazebo_relay'
        node=CrawlController(nav_robot_model,profile,'gazebo' if relay else 'mujoco',context=context,
            cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'] if relay else [],
            parameter_overrides=[Parameter('validation_mode',value=relay),
                Parameter('control_clock_mode',value='relay100' if relay else 'native')])
    try:
        node.trigger_configure()
        assert node.machine is not None
        expected_policy='bounded_preload' if scope=='gazebo_relay' else 'loaded_quintic'
        assert node.machine.calibration_return_policy==expected_policy
        assert node.command_publication_count==0 and not node.active
    finally:
        node.destroy_node();context.try_shutdown()


@pytest.mark.parametrize('policy',['loaded_quintic','bounded_preload'])
def test_g1_owner_transmits_its_policy_to_the_vertical_trajectory(nav_robot_model,policy):
    plant=IdealFeedback(nav_robot_model)
    machine=CrawlMachine(nav_robot_model,default_limits(),calibration_return_policy=policy)
    machine.reset(plant.state,plant.ros,plant.wall)
    machine.request_contact_calibration()
    for _ in range(400):
        result=machine.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(machine,result)
        if machine._calibration_vertical is not None:
            assert machine._calibration_vertical.return_policy==policy
            return
    pytest.fail('calibration never reached vertical owner')
