"""Explicit approved comparison only; schema fixtures are never engine proof."""
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path

import pytest
from launch import LaunchContext
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters

from integrated_robot_navigation.carry_profile import validate_profile
from integrated_robot_navigation.execution_contract import g2_execution_profile
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import materialize_scene
from test_native_profile_admission import prepared, sha


def relay_proof(directory, model, physics_hash):
    profile, result = prepared(directory, model)
    result['native_physics_sha256'] = physics_hash
    result['execution_mode']['control_clock'] = 'relay100'
    result['required_checks'].append('control_clock_contract')
    result['checks']['control_clock_contract'] = True
    path = directory/'result.json'
    path.write_text(json.dumps(result))
    profile = replace(profile, state='native_validated', native_evidence={
        'mujoco': dict(path=str(path), sha256=sha(path))})
    return profile, result, path


def test_mujoco_relay_requires_exact_g1_mode_and_extra_clock_proof(tmp_path, nav_robot_model):
    scene = dict(engine='mujoco', native_physics_sha256='a'*64)
    expected = g2_execution_profile(scene, 'relay100')
    profile, result, path = relay_proof(tmp_path, nav_robot_model, 'a'*64)
    assert validate_profile(profile, nav_robot_model, 'mujoco', execution_profile=expected) == (True, '')
    assert not validate_profile(profile, nav_robot_model, 'mujoco')[0]
    assert not validate_profile(profile, nav_robot_model, 'mujoco',
        execution_profile=g2_execution_profile(scene, 'native'))[0]
    result['required_checks'].remove('control_clock_contract')
    path.write_text(json.dumps(result))
    profile = replace(profile, native_evidence={'mujoco': dict(path=str(path), sha256=sha(path))})
    assert validate_profile(profile, nav_robot_model, 'mujoco', execution_profile=expected) == (False, 'evidence_checks')


@pytest.mark.parametrize('field,value', [
    ('position_reference_mode', 'g1_ramp20ms'),
    ('dart_contact_mode', 'allowance50um'),
    ('native_physics_sha256', ''),
])
def test_mujoco_clock_comparison_never_imports_gazebo_physics(field, value):
    scene = dict(engine='mujoco', native_physics_sha256='a'*64)
    scene[field] = value
    with pytest.raises(ValueError):
        g2_execution_profile(scene, 'relay100')


def test_mujoco_relay_launch_routes_only_five_consumers_and_retains_g2_scope(tmp_path):
    scene = materialize_scene('mujoco', 'g1', tmp_path/'scene')
    model = compile_model(Path(scene['robot']['path']).read_text())
    proof = tmp_path/'proof'
    proof.mkdir()
    profile, _, _ = relay_proof(proof, model, scene['native_physics_sha256'])
    profile_path = tmp_path/'profile.json'
    profile_path.write_text(json.dumps(asdict(profile)))
    launch_file = Path(__file__).resolve().parents[1]/'launch/crawl_system.launch.py'
    spec = importlib.util.spec_from_file_location('mujoco_clock_scope_launch', launch_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    context = LaunchContext()
    context.launch_configurations.update(engine='mujoco', navigation_scene=str(tmp_path/'scene'),
        carry_profile=str(profile_path), validation_mode='true', g2_validation_mode='true',
        control_clock_mode='relay100')
    actions = [a for a in module.launch_nodes(context) if isinstance(a, Node)]
    remapped = [a for a in actions if a._Node__remappings]
    assert len(remapped) == 5
    scoped = [p for a in actions for p in evaluate_parameters(context, a._Node__parameters)
        if isinstance(p, dict) and p.get('g2_validation_mode') is True]
    assert len(scoped) == 2
    assert all(json.loads(p['native_execution_profile']) == g2_execution_profile(scene, 'relay100') for p in scoped)
    context.launch_configurations['validation_mode'] = 'false'
    with pytest.raises(ValueError):
        module.launch_nodes(context)


def test_clock_comparison_adds_checks_without_removing_existing_mujoco_acceptance():
    from run_navigation_13_5 import native_required_checks, g2_required_checks
    for scenario in ('crawl-cycle', 'crawl-reverse'):
        old = g2_required_checks('native', 'native', 'mujoco', scenario)
        assert g2_required_checks('relay100', 'native', 'mujoco', scenario) == old | {'control_clock_contract'}
    assert native_required_checks('relay100', 'native', 'mujoco') == (
        native_required_checks('native', 'native', 'mujoco') | {'control_clock_contract'})


def test_mujoco_explicit_g2_guard_admission_over_actual_service(tmp_path, nav_robot_model):
    """Real ROS service, synthetic sensor/proof fixture; never physics acceptance."""
    import rclpy
    from rclpy.context import Context
    from rclpy.parameter import Parameter
    from integrated_robot_navigation.motion_guard import MotionGuardNode
    from test_motion_guard_ros import Rig
    profile, _, _ = relay_proof(tmp_path, nav_robot_model, 'a'*64)
    expected = g2_execution_profile(dict(engine='mujoco', native_physics_sha256='a'*64), 'relay100')
    context = Context()
    rclpy.init(context=context)
    node = rig = None
    try:
        node = MotionGuardNode(nav_robot_model, profile, 'mujoco', context=context,
            parameter_overrides=[Parameter('use_sim_time', value=True),
                Parameter('validation_mode', value=True), Parameter('g2_validation_mode', value=True),
                Parameter('native_execution_profile', value=json.dumps(expected))])
        rig = Rig(node, nav_robot_model, context)
        rig.pump(.5)
        assert rig.mode('CRAWL').accepted
    finally:
        if rig is not None:
            rig.close()
        elif node is not None:
            node.destroy_node()
        context.try_shutdown()
