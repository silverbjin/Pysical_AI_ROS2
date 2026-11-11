import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
import rclpy
from rclpy.context import Context
from launch import LaunchContext


@pytest.mark.parametrize('scenario', ['level2_obstacles', 'level3_house'])
def test_survey_and_final_checkers_survive_actual_ros_parser(monkeypatch, scenario):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', 'carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO', scenario)
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2', '0')
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('survey_launch', source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_package_share_directory',lambda name:str(source.parents[1]))
    action=next(a for a in module.generate_launch_description().entities if getattr(a,'_Node__node_name',None)=='controller_server')
    files=[p for p in action._Node__parameters if hasattr(p,'evaluate')]
    args=['--ros-args']
    for p in files:args+=['--params-file',str(p.evaluate(LaunchContext()))]
    context=Context();node=None;rclpy.init(context=context)
    try:
        node=rclpy.create_node('controller_server',context=context,use_global_arguments=False,cli_args=args,automatically_declare_parameters_from_overrides=True)
        assert node.get_parameter('goal_checker_plugins').value==['goal_checker','survey_checker']
        assert node.get_parameter('goal_checker.xy_goal_tolerance').value==.015
        assert node.get_parameter('survey_checker.xy_goal_tolerance').value==.06
        assert node.get_parameter('survey_checker.yaw_goal_tolerance').value==.06
        assert node.get_parameter('survey_checker.stateful').value is True
        assert node.get_parameter('survey_checker.plugin').value=='nav2_controller::SimpleGoalChecker'
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()


def test_survey_action_selects_installed_xml_without_changing_default(monkeypatch):
    from ch13_system_validation import survey
    share=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse'
    monkeypatch.setattr(survey,'get_package_share_directory',lambda name:str(share))
    goal=survey.make_survey_goal((1.,2.,0.),123000000)
    assert Path(goal.behavior_tree)==share/'config/navigate_survey.xml'
    assert ET.parse(goal.behavior_tree).find('.//FollowPath').attrib['goal_checker_id']=='survey_checker'
    assert ET.parse(share/'config/navigate_no_recovery.xml').find('.//FollowPath').attrib['goal_checker_id']=='goal_checker'
