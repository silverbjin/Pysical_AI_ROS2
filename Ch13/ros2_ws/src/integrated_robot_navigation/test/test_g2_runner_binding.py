"""Small schema fixtures verify preflight binding, never native success."""
from dataclasses import replace
import json
from pathlib import Path
import pytest
import run_navigation_13_5 as runner
from test_execution_admission_contract import fixture


def inputs(tmp_path,model):
    profile,execution=fixture(tmp_path,model,'mujoco')
    result=Path(profile.native_evidence['mujoco']['path'])
    original=json.loads(result.read_text())
    scene=dict(engine='mujoco',native_physics_sha256=execution['native_physics_sha256'],
        position_reference_mode='native',dart_contact_mode='native')
    source=json.loads((tmp_path/'source_manifest.json').read_text())
    installed=json.loads((tmp_path/'install_manifest.json').read_text())
    return replace(profile,state='offline',native_evidence={}),result,scene,source,installed


def test_g2_preflight_derives_a_new_profile_only_from_matching_complete_g1(tmp_path,nav_robot_model):
    assert hasattr(runner,'prepare_g2_profile'),'G2 evidence-bound preflight missing'
    profile,result,scene,source,installed=inputs(tmp_path,nav_robot_model)
    admitted,execution=runner.prepare_g2_profile(profile,nav_robot_model,'mujoco',scene,'native',result,source,installed)
    assert admitted.state=='native_validated' and profile.state=='offline'
    assert admitted.native_evidence['mujoco']['path']==str(result.resolve())
    assert execution['native_physics_sha256']==scene['native_physics_sha256']


@pytest.mark.parametrize('bad',['missing','source','installation','physics'])
def test_g2_cannot_inherit_stale_code_installation_or_other_native_physics(tmp_path,nav_robot_model,bad):
    assert hasattr(runner,'prepare_g2_profile'),'G2 evidence-bound preflight missing'
    profile,result,scene,source,installed=inputs(tmp_path,nav_robot_model)
    if bad=='missing':result=None
    elif bad=='source':source['files']['example.py']='1'*64
    elif bad=='installation':installed['example']['changed']=True
    else:scene['native_physics_sha256']='b'*64
    with pytest.raises((ValueError,RuntimeError)):
        runner.prepare_g2_profile(profile,nav_robot_model,'mujoco',scene,'native',result,source,installed)


def test_g2_required_checks_keep_cycle_reverse_and_all_runtime_safety_separate():
    assert hasattr(runner,'g2_required_checks'),'G2 required-check contract missing'
    from verify_navigation_13_5 import G2_REQUIRED
    cycle=runner.g2_required_checks('native','native','mujoco','crawl-cycle')
    assert G2_REQUIRED.issubset(cycle)
    assert {'g1_profile_verified','crawl_admission_accepted','bounded_test_commands','command_source_shutdown'}.issubset(cycle)
    reverse=runner.g2_required_checks('native','native','mujoco','crawl-reverse')
    assert {'reverse','stand10','stopped','normal_runtime_exit','normal_engine_exit'}.issubset(reverse)
    assert runner.native_required_checks('native','native','mujoco')!=cycle
