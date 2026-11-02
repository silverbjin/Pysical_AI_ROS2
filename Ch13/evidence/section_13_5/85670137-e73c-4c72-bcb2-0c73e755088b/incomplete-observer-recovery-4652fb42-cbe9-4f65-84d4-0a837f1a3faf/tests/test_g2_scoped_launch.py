"""Evaluate actual launch actions; small proof fixtures are unit-only."""
from dataclasses import asdict,replace
import importlib.util
import json
from pathlib import Path
import pytest
from launch import LaunchContext
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
from integrated_robot_navigation.scene import materialize_scene
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.execution_contract import g2_execution_profile
from test_native_profile_admission import prepared,sha


def setup(tmp_path,engine,*,validated=True,g2=True):
    scene=materialize_scene(engine,'g1',tmp_path/'scene',g1_reference_ramp=engine=='gazebo',
        g1_contact_allowance=engine=='gazebo')
    model=compile_model(Path(scene['robot']['path']).read_text())
    proof=tmp_path/'proof';proof.mkdir();profile,result=prepared(proof,model)
    clock='relay100' if engine=='gazebo' else 'native';expected=g2_execution_profile(scene,clock)
    result.update(engine=engine,scene=scene,native_physics_sha256=scene['native_physics_sha256'])
    result['execution_mode'].update(control_clock=clock,dart_contact=expected['dart_contact'])
    if engine=='gazebo':
        for check in ('control_clock_contract','dart_contact_contract'):
            result['required_checks'].append(check);result['checks'][check]=True
    path=proof/'result.json';path.write_text(json.dumps(result))
    if validated:profile=replace(profile,state='native_validated',native_evidence={engine:dict(path=str(path),sha256=sha(path))})
    profile_file=tmp_path/'profile.json';profile_file.write_text(json.dumps(asdict(profile)))
    launch_file=Path(__file__).resolve().parents[1]/'launch/crawl_system.launch.py'
    spec=importlib.util.spec_from_file_location('scoped_g2_launch',launch_file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    context=LaunchContext();context.launch_configurations.update(engine=engine,navigation_scene=str(tmp_path/'scene'),
        carry_profile=str(profile_file),validation_mode='true',g2_validation_mode=str(g2).lower(),control_clock_mode=clock)
    return module,context,expected


@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_only_guard_and_crawl_receive_the_verified_actual_g2_execution_contract(tmp_path,engine):
    module,context,expected=setup(tmp_path,engine)
    actions=module.launch_nodes(context)
    parameters=[p for action in actions if isinstance(action,Node)
        for p in evaluate_parameters(context,action._Node__parameters) if isinstance(p,dict)]
    scoped=[p for p in parameters if p.get('g2_validation_mode') is True]
    assert len(scoped)==2,'G2 scope not routed to exactly the guard and sole crawl owner'
    assert all(json.loads(p['native_execution_profile'])==expected for p in scoped)


@pytest.mark.parametrize('engine',['mujoco','gazebo'])
def test_offline_profile_cannot_enter_the_g2_launch(tmp_path,engine):
    module,context,_=setup(tmp_path,engine,validated=False)
    with pytest.raises(ValueError,match='G2|native_validation'):module.launch_nodes(context)


def test_g1_path_does_not_implicitly_expand_into_g2(tmp_path):
    module,context,_=setup(tmp_path,'mujoco',validated=False,g2=False)
    actions=module.launch_nodes(context)
    for action in actions:
        if isinstance(action,Node):
            for parameters in evaluate_parameters(context,action._Node__parameters):
                if isinstance(parameters,dict):assert parameters.get('g2_validation_mode',False) is False
