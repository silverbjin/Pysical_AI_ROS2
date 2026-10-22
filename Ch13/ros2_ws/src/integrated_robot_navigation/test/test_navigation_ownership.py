"""Evaluate launch actions/parameters; no duplicate legacy command owner."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path

import pytest
from launch import LaunchContext
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from rclpy.parameter import Parameter
import rclpy
from rclpy.context import Context
from integrated_robot_navigation.carry_profile import prepare_profile
from integrated_robot_navigation import scene
from guard_fixture import CARRY
from test_motion_guard_ros import Rig
from test_crawl_lifecycle import crawl_rig
from lifecycle_msgs.msg import Transition


def launch_file(name):
    path = Path(__file__).resolve().parents[1]/'launch'/(name+'.launch.py')
    assert path.is_file(), 'exclusive navigation launch missing: '+name
    spec = importlib.util.spec_from_file_location('nav_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('engine', ['mujoco', 'gazebo'])
def test_launch_graph_has_exact_owners_and_bound_sensor_scene(tmp_path, engine):
    record = scene.materialize_scene(engine, 'g1', tmp_path/'scene')
    from integrated_robot_navigation.model import compile_model
    model = compile_model(Path(record['robot']['path']).read_text())
    profile = tmp_path/'profile.json'
    profile.write_text(json.dumps(asdict(prepare_profile(model, CARRY))))
    ctx = LaunchContext()
    ctx.launch_configurations.update(engine=engine, navigation_scene=str(tmp_path/'scene'),
                                    carry_profile=str(profile), validation_mode='true')
    module = launch_file('crawl_system')
    actions = module.launch_nodes(ctx)
    nodes = [a for a in actions if isinstance(a, Node)]
    executables = [a.node_executable for a in nodes]
    assert sorted(executables) == sorted(['motion_guard', 'crawl_controller', 'carry_manager',
                                          'nav_projection', 'crawl_startup'])
    for action in nodes:
        values = evaluate_parameters(ctx, action._Node__parameters)
        assert any(isinstance(p, dict) and p.get('use_sim_time') is True for p in values)
    selected = launch_file('navigation_sensors').select_engine(ctx)
    included = [a for a in selected if isinstance(a, IncludeLaunchDescription)]
    assert len(included) == 1
    included[0].launch_description_source.get_launch_description(ctx)
    assert included[0].launch_description_source.location.endswith(engine+'.launch.py')
    arguments = {key: perform_substitutions(ctx, normalize_to_list_of_substitutions(value))
                 for key, value in included[0].launch_arguments}
    assert arguments['navigation_enabled'] == 'true'
    assert arguments['navigation_scene'] == str(tmp_path/'scene')
    if engine == 'gazebo':
        adapter = next(a for a in selected if isinstance(a, Node))
        values = evaluate_parameters(ctx, adapter._Node__parameters)
        assert any(isinstance(p, dict) and p.get('scene_dir') == str(tmp_path/'scene') for p in values)


def test_validation_mode_denies_crawl_even_with_validated_admission(nav_robot_model, monkeypatch):
    from integrated_robot_navigation import motion_guard
    monkeypatch.setattr(motion_guard, 'validate_profile', lambda *args: (True, 'admission_stub'))
    ctx = Context()
    rclpy.init(context=ctx)
    guard = motion_guard.MotionGuardNode(nav_robot_model, prepare_profile(nav_robot_model, CARRY),
        'mujoco', context=ctx, parameter_overrides=[Parameter('use_sim_time', value=True),
                                                  Parameter('validation_mode', value=True)])
    rig = Rig(guard, nav_robot_model, ctx)
    try:
        rig.pump(.3)
        response = rig.mode('CRAWL')
        assert not response.accepted and 'validation' in response.message
    finally:
        rig.close()
        ctx.try_shutdown()


@pytest.mark.parametrize('crawl_rig', [True], indirect=True)
def test_validation_mode_leg_owner_rejects_external_crawl_flag(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    rig.guard.admission = (True, 'test_only_native_admission_stub')
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.mode_name, rig.value = 'CRAWL', .001
    rig.pump(.12)
    assert rig.crawl_states[-1].state == 'FAULT'
    assert rig.crawl_states[-1].fault_reason == 'validation_mode_forbids_crawl'
    count = len(rig.commands)
    rig.pump(.08)
    assert len(rig.commands) == count
