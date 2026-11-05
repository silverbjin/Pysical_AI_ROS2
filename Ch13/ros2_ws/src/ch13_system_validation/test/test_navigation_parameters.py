"""Resolve the actual launch file and feed its YAML to the real ROS parser."""
import importlib.util
from pathlib import Path

import pytest
import rclpy
from launch import LaunchContext
from rclpy.context import Context


@pytest.mark.parametrize('profile,scenario,expected,stateful', [('', 'level1_floor', .06,True),
    ('carry_v1', 'development', .06,True), ('carry_v1', 'level1_floor', .015,True),
    ('carry_v1','level2_obstacles',.015,False),('carry_v1','level3_house',.015,False)])
def test_book_goal_tolerance_survives_node_specific_ros_yaml(tmp_path, monkeypatch, profile, scenario, expected,stateful):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', profile)
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO', scenario)
    source = Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec = importlib.util.spec_from_file_location('precision_launch', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    controller = next(a for a in module.generate_launch_description().entities
                      if getattr(a, '_Node__node_name', None) == 'controller_server')
    parameter_file = controller._Node__parameters[0]
    path = Path(parameter_file.evaluate(LaunchContext()))
    context = Context()
    node = None
    rclpy.init(context=context)
    try:
        node = rclpy.create_node('controller_server', context=context, use_global_arguments=False,
            cli_args=['--ros-args', '--params-file', str(path)],
            automatically_declare_parameters_from_overrides=True)
        assert node.get_parameter('goal_checker.xy_goal_tolerance').value == expected
        assert node.get_parameter('goal_checker.yaw_goal_tolerance').value == .06
        assert node.get_parameter('goal_checker.stateful').value is stateful
        assert node.get_parameter('FollowPath.desired_linear_vel').value == .15
    finally:
        if node is not None: node.destroy_node()
        context.shutdown()
        parameter_file.cleanup()
