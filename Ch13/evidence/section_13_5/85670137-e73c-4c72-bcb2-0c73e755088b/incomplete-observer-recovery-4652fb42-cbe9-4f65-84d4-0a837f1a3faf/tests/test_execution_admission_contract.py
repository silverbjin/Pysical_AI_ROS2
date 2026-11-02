"""Unit fixtures only: G1 experiments require an exact explicit G2 contract."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import pytest
from integrated_robot_navigation import carry_profile as api
from test_native_profile_admission import prepared,sha


def contract(engine='gazebo'):
    return dict(control_clock='relay100' if engine=='gazebo' else 'native',
        position_reference_mode='g1_ramp20ms' if engine=='gazebo' else 'native',
        dart_contact='allowance50um' if engine=='gazebo' else 'native',native_physics_sha256='a'*64)


def fixture(tmp_path,model,engine):
    profile,result=prepared(tmp_path,model);expected=contract(engine)
    result['engine']=engine;result['native_physics_sha256']=expected['native_physics_sha256']
    result['execution_mode'].update(control_clock=expected['control_clock'],dart_contact=expected['dart_contact'])
    result['scene']['position_reference_mode']=expected['position_reference_mode']
    result['scene']['dart_contact_mode']=expected['dart_contact']
    if engine=='gazebo':
        for name in ('dart_contact_contract','control_clock_contract'):
            result['required_checks'].append(name);result['checks'][name]=True
    path=tmp_path/'result.json';path.write_text(json.dumps(result))
    profile=replace(profile,state='native_validated',native_evidence={engine:dict(path=str(path),sha256=sha(path))})
    return profile,expected


@pytest.mark.parametrize('engine',['gazebo','mujoco'])
def test_exact_runtime_contract_is_required_in_addition_to_native_g1_result(tmp_path,nav_robot_model,engine):
    profile,expected=fixture(tmp_path,nav_robot_model,engine)
    assert api.validate_profile(profile,nav_robot_model,engine,execution_profile=expected)==(True,'')


@pytest.mark.parametrize('field,value',[
    ('control_clock','native'),('position_reference_mode','native'),('dart_contact','native'),
    ('native_physics_sha256','b'*64),('native_physics_sha256','')])
def test_changed_actual_mode_or_physics_never_inherits_g1_proof(tmp_path,nav_robot_model,field,value):
    profile,expected=fixture(tmp_path,nav_robot_model,'gazebo');expected[field]=value
    assert api.validate_profile(profile,nav_robot_model,'gazebo',execution_profile=expected)[0] is False


def test_explicit_contract_does_not_make_the_default_admission_accept_an_experiment(tmp_path,nav_robot_model):
    profile,expected=fixture(tmp_path,nav_robot_model,'gazebo')
    assert api.validate_profile(profile,nav_robot_model,'gazebo')[0] is False


def test_profile_builder_uses_the_bound_scene_hash_not_a_recomputed_model_alias():
    assert importlib.util.find_spec('integrated_robot_navigation.execution_contract'),'explicit G2 execution contract missing'
    from integrated_robot_navigation.execution_contract import g2_execution_profile
    scene=dict(engine='gazebo',native_physics_sha256='a'*64,
        position_reference_mode='g1_ramp20ms',dart_contact_mode='allowance50um')
    assert g2_execution_profile(scene,'relay100')==contract()
    with pytest.raises(ValueError):g2_execution_profile(scene,'native')
