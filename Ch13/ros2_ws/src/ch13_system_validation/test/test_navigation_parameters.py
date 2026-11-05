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
        controller_stateful=node.get_parameter('FollowPath.stateful').value if node.has_parameter('FollowPath.stateful') else True
        assert controller_stateful is stateful
        assert node.get_parameter('FollowPath.desired_linear_vel').value == .15
    finally:
        if node is not None: node.destroy_node()
        context.shutdown()
        parameter_file.cleanup()


@pytest.mark.parametrize('scenario,cap',[('level2_obstacles',.10),('level3_house',.20),('development',.20)])
def test_level2_turn_cap_uses_actual_node_specific_array_parameters(monkeypatch,scenario,cap):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('turn_cap_launch',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_package_share_directory',lambda name:str(source.parents[1]))
    smoother=next(a for a in module.generate_launch_description().entities
                  if getattr(a,'_Node__node_name',None)=='velocity_smoother')
    files=[p for p in smoother._Node__parameters if hasattr(p,'evaluate')]
    args=['--ros-args']
    for p in files:args+=['--params-file',str(p.evaluate(LaunchContext()))]
    context=Context();node=None;rclpy.init(context=context)
    try:
        node=rclpy.create_node('velocity_smoother',context=context,use_global_arguments=False,
            cli_args=args,automatically_declare_parameters_from_overrides=True)
        assert list(node.get_parameter('max_velocity').value)==[.20,0.,cap]
        assert list(node.get_parameter('min_velocity').value)==[0.,0.,-cap]
        assert list(node.get_parameter('max_accel').value)==[.30,0.,.50]
        assert node.get_parameter('scale_velocities').value is (scenario in ('level2_obstacles','level3_house'))
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()

@pytest.mark.parametrize('scenario,heading_aware',[('development',False),('level1_floor',False),('level2_obstacles',True),('level3_house',True)])
def test_book_heading_planner_preserves_forward_motion_and_legacy(monkeypatch,scenario,heading_aware):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('heading_launch',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_package_share_directory',lambda name:str(source.parents[1]))
    planner=next(a for a in module.generate_launch_description().entities if getattr(a,'_Node__node_name',None)=='planner_server')
    files=[p for p in planner._Node__parameters if hasattr(p,'evaluate')];args=['--ros-args']
    for p in files:args+=['--params-file',str(p.evaluate(LaunchContext()))]
    context=Context();node=None;rclpy.init(context=context)
    try:
        node=rclpy.create_node('planner_server',context=context,use_global_arguments=False,cli_args=args,
            automatically_declare_parameters_from_overrides=True)
        expected='nav2_smac_planner::SmacPlannerHybrid' if heading_aware else 'nav2_navfn_planner::NavfnPlanner'
        assert node.get_parameter('GridBased.plugin').value==expected
        if heading_aware:
            assert node.get_parameter('GridBased.motion_model_for_search').value=='DUBIN'
            assert node.get_parameter('GridBased.minimum_turning_radius').value==.3
            assert node.get_parameter('GridBased.max_planning_time').value==2.
            assert node.get_parameter('GridBased.cache_obstacle_heuristic').value is False
            assert node.get_parameter('GridBased.smooth_path').value is False
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()
