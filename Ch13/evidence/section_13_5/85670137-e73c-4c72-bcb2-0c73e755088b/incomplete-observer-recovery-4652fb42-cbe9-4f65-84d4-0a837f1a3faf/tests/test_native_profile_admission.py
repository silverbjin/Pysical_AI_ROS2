"""Unit-only runner-schema fixtures; these are NEVER physical G1 evidence."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import uuid

import pytest
from integrated_robot_navigation import carry_profile as api
from guard_fixture import CARRY
from run_navigation_13_5 import native_required_checks


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepared(tmp_path,model):
    profile=api.prepare_profile(model,CARRY)
    required=native_required_checks('native','native','mujoco')
    result=dict(schema_version=1,run_id=str(uuid.uuid4()),kind='native',gate='G1',engine='mujoco',
        status='PASS',errors=[],model_sha256=profile.model_sha256,config_sha256=profile.config_sha256,
        physics_sha256=profile.physics_sha256,required_checks=sorted(required),
        checks={key:True for key in required},
        execution_mode=dict(control_clock='native',dart_contact='native',validation_only=True,
                            diagnostic_profile_node=None),
        scene=dict(position_reference_mode='native',dart_contact_mode='native'),artifacts=[])
    contents={'frames.json':{'root_source':'native_ground_truth'},
        'action_results.json':dict(terminal=True,result_future_done=True,result_status=4,
            result_error_code=0,pending_uuid=None,model_sha256=model.model_sha256),
        'source_manifest.json':{'files':{'example.py':'0'*64}},'install_manifest.json':{'example':{}},
        'teardown.json':dict(runtime_exit=True,engine_exit=True,parent_reaped=True,
            launch_returncode=0,engine_returncodes=[0],forced_cleanup=False,residual_live_pids=[])}
    for name,value in contents.items():
        file=tmp_path/name;file.write_text(json.dumps(value))
        result['artifacts'].append(dict(path=name,size=file.stat().st_size,sha256=sha(file)))
    return profile,result


def validate(tmp_path,model,profile,result):
    path=tmp_path/'result.json';path.write_text(json.dumps(result))
    candidate=replace(profile,state='native_validated',native_evidence={
        'mujoco':dict(path=str(path),sha256=sha(path))})
    return api.validate_profile(candidate,model,'mujoco')


def test_actual_runner_artifact_list_shape_can_be_checked_without_a_handwritten_role_map(tmp_path,nav_robot_model):
    profile,result=prepared(tmp_path,nav_robot_model)
    assert validate(tmp_path,nav_robot_model,profile,result)==(True,'')


@pytest.mark.parametrize('bad',['missing_required','false_extra','duplicate','traversal','changed_bytes',
    'missing_artifact','forced','no_terminal','experiment','wrong_binding','malformed_action'])
def test_incomplete_mismatched_or_g1_experiment_evidence_cannot_enable_native_crawl(tmp_path,nav_robot_model,bad):
    profile,result=prepared(tmp_path,nav_robot_model)
    if bad=='missing_required':result['required_checks'].remove('contact_lift')
    elif bad=='false_extra':
        result['required_checks'].append('extra_required');result['checks']['extra_required']=False
    elif bad=='duplicate':result['artifacts'].append(result['artifacts'][0])
    elif bad=='traversal':result['artifacts'][0]['path']='../frames.json'
    elif bad=='changed_bytes':(tmp_path/'frames.json').write_text('changed')
    elif bad=='missing_artifact':result['artifacts']=result['artifacts'][1:]
    elif bad in ('forced','no_terminal'):
        name='teardown.json' if bad=='forced' else 'action_results.json'
        file=tmp_path/name;data=json.loads(file.read_text())
        data['forced_cleanup' if bad=='forced' else 'result_future_done']=True if bad=='forced' else False
        file.write_text(json.dumps(data))
        artifact=next(row for row in result['artifacts'] if row['path']==name)
        artifact.update(size=file.stat().st_size,sha256=sha(file))
    elif bad=='experiment':result['execution_mode']['control_clock']='relay100'
    elif bad=='malformed_action':
        file=tmp_path/'action_results.json';file.write_text('[]')
        artifact=next(row for row in result['artifacts'] if row['path']==file.name)
        artifact.update(size=file.stat().st_size,sha256=sha(file))
    else:result['config_sha256']='0'*64
    assert validate(tmp_path,nav_robot_model,profile,result)[0] is False
