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
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2','1')
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
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2','1')
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
        assert list(node.get_parameter('min_velocity').value)==[-.1 if scenario in ('level2_obstacles','level3_house') else 0.,0.,-cap]
        assert list(node.get_parameter('max_accel').value)==[.30,0.,.50]
        assert node.get_parameter('scale_velocities').value is (scenario in ('level2_obstacles','level3_house'))
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()

@pytest.mark.parametrize('scenario,heading_aware',[('development',False),('level1_floor',False),('level2_obstacles',True),('level3_house',True)])
def test_book_heading_planner_preserves_forward_motion_and_legacy(monkeypatch,scenario,heading_aware):
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2','1')
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
            assert node.get_parameter('GridBased.motion_model_for_search').value=='REEDS_SHEPP'
            assert node.get_parameter('GridBased.minimum_turning_radius').value==.3
            assert node.get_parameter('GridBased.max_planning_time').value==2.
            assert node.get_parameter('GridBased.cache_obstacle_heuristic').value is False
            assert node.get_parameter('GridBased.smooth_path').value is False
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()

@pytest.mark.parametrize('scenario,book',[('development',False),('level1_floor',False),('level2_obstacles',True),('level3_house',True)])
def test_reverse_primary_and_goal_rotation_are_separate_stateless_boundaries(monkeypatch,scenario,book):
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2','1')
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('reverse_launch',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_package_share_directory',lambda name:str(source.parents[1]))
    action=next(a for a in module.generate_launch_description().entities if getattr(a,'_Node__node_name',None)=='controller_server')
    files=[p for p in action._Node__parameters if hasattr(p,'evaluate')];args=['--ros-args']
    for p in files:args+=['--params-file',str(p.evaluate(LaunchContext()))]
    context=Context();node=None;rclpy.init(context=context)
    try:
        node=rclpy.create_node('controller_server',context=context,use_global_arguments=False,cli_args=args,automatically_declare_parameters_from_overrides=True)
        primary='nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController'
        assert node.get_parameter('FollowPath.plugin').value==('nav2_rotation_shim_controller::RotationShimController' if book else primary)
        assert node.get_parameter('FollowPath.use_rotate_to_heading').value is (not book)
        assert node.get_parameter('FollowPath.allow_reversing').value is book
        assert node.get_parameter('FollowPath.rotate_to_heading_angular_vel').value==.15
        assert node.get_parameter('FollowPath.max_angular_accel').value==.5
        if book:
            assert node.get_parameter('FollowPath.primary_controller').value==primary
            for key in ('rotate_to_goal_heading','rotate_to_heading_once','use_path_orientations'):assert node.get_parameter('FollowPath.'+key).value is True
            for key in ('.position_checker.stateful','FollowPath.position_checker.stateful'):assert node.get_parameter(key).value is False
    finally:
        if node is not None:node.destroy_node()
        context.shutdown()
        for p in files:p.cleanup()

@pytest.mark.parametrize('scenario,cap',[('level2_obstacles',.1),('level3_house',.2)])
def test_default_book_reuses_verified_forward_controllers_and_checker_policy(monkeypatch,scenario,cap):
    monkeypatch.delenv('CH13_EXPERIMENTAL_SE2',raising=False)
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1');monkeypatch.setenv('CH13_VALIDATION_SCENARIO',scenario)
    source=Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec=importlib.util.spec_from_file_location('default_baseline_launch',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_package_share_directory',lambda name:str(source.parents[1]))
    actions=module.generate_launch_description().entities
    for name in ('planner_server','controller_server','velocity_smoother'):
        action=next(a for a in actions if getattr(a,'_Node__node_name',None)==name)
        files=[p for p in action._Node__parameters if hasattr(p,'evaluate')];args=['--ros-args']
        for p in files:args+=['--params-file',str(p.evaluate(LaunchContext()))]
        context=Context();node=None;rclpy.init(context=context)
        try:
            node=rclpy.create_node(name,context=context,use_global_arguments=False,cli_args=args,automatically_declare_parameters_from_overrides=True)
            if name=='planner_server':
                assert node.get_parameter('GridBased.plugin').value==('nav2_smac_planner::SmacPlannerHybrid' if scenario=='level2_obstacles' else 'nav2_navfn_planner::NavfnPlanner')
                if scenario=='level2_obstacles':
                    assert node.get_parameter('GridBased.motion_model_for_search').value=='DUBIN'
                    assert node.get_parameter('GridBased.minimum_turning_radius').value==.3
                    assert node.get_parameter('GridBased.tolerance').value==.01
                    assert node.get_parameter('GridBased.cache_obstacle_heuristic').value is False
                    assert node.get_parameter('GridBased.smooth_path').value is False
            elif name=='controller_server':
                assert node.get_parameter('FollowPath.plugin').value=='nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController'
                assert node.get_parameter('goal_checker.xy_goal_tolerance').value==.015
                assert node.get_parameter('goal_checker.yaw_goal_tolerance').value==.06
                assert node.get_parameter('goal_checker.stateful').value is (scenario!='level2_obstacles')
                assert (node.get_parameter('FollowPath.stateful').value if node.has_parameter('FollowPath.stateful') else True) is (scenario!='level2_obstacles')
                assert node.get_parameter('FollowPath.use_rotate_to_heading').value is True
                assert node.get_parameter('FollowPath.allow_reversing').value is False
            else:
                assert list(node.get_parameter('min_velocity').value)==[0.,0.,-cap]
                assert list(node.get_parameter('max_velocity').value)==[.2,0.,cap]
        finally:
            if node is not None:node.destroy_node()
            context.shutdown()
            for p in files:p.cleanup()
@pytest.mark.parametrize('scenario,experimental,enabled', [
    ('level2_obstacles', False, True), ('level2_obstacles', True, False),
    ('level1_floor', False, False), ('level3_house', False, False),
    ('development', False, False)])
def test_goal_extension_is_scoped_to_default_level2_rpp(monkeypatch, scenario, experimental, enabled):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE', 'carry_v1')
    monkeypatch.setenv('CH13_VALIDATION_SCENARIO', scenario)
    monkeypatch.setenv('CH13_EXPERIMENTAL_SE2', '1' if experimental else '0')
    source = Path(__file__).resolve().parents[2]/'ch13_navigation_reuse/launch/navigation.launch.py'
    spec = importlib.util.spec_from_file_location('goal_extension_launch', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name: str(source.parents[1]))
    action = next(a for a in module.generate_launch_description().entities
                  if getattr(a, '_Node__node_name', None) == 'controller_server')
    files = [p for p in action._Node__parameters if hasattr(p, 'evaluate')]
    args = ['--ros-args']
    for p in files:
        args += ['--params-file', str(p.evaluate(LaunchContext()))]
    context = Context()
    node = None
    rclpy.init(context=context)
    try:
        node = rclpy.create_node('controller_server', context=context, use_global_arguments=False,
            cli_args=args, automatically_declare_parameters_from_overrides=True)
        for key in ('use_fixed_curvature_lookahead', 'interpolate_curvature_after_goal'):
            name = 'FollowPath.'+key
            assert (node.get_parameter(name).value if node.has_parameter(name) else False) is enabled
        if enabled:
            assert node.get_parameter('FollowPath.curvature_lookahead_dist').value == .25
            assert node.get_parameter('FollowPath.lookahead_dist').value == .45
            assert node.get_parameter('FollowPath.allow_reversing').value is False
            assert node.get_parameter('FollowPath.use_rotate_to_heading').value is True
            assert node.get_parameter('FollowPath.use_collision_detection').value is True
            assert node.get_parameter('FollowPath.stateful').value is False
            assert node.get_parameter('goal_checker.stateful').value is False
            assert node.get_parameter('goal_checker.xy_goal_tolerance').value == .015
            assert node.get_parameter('goal_checker.yaw_goal_tolerance').value == .06
            assert node.get_parameter('FollowPath.desired_linear_vel').value == .15
            assert node.get_parameter('FollowPath.max_angular_accel').value == .5
    finally:
        if node is not None:
            node.destroy_node()
        context.shutdown()
        for p in files:
            p.cleanup()
