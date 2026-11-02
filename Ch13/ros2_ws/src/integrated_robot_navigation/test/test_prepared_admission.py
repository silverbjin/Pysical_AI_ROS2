"""Keep artifact hashing outside control services; local receipts stay fail-closed."""
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from test_native_profile_admission import prepared,sha


def module():
    assert importlib.util.find_spec('integrated_robot_navigation.admission'),'prepared admission boundary missing'
    from integrated_robot_navigation import admission
    return admission


def candidate(tmp_path,model):
    profile,result=prepared(tmp_path,model);path=tmp_path/'result.json';path.write_text(json.dumps(result))
    return replace(profile,state='native_validated',native_evidence={'mujoco':dict(path=str(path),sha256=sha(path))})


def test_prepared_check_never_rehashes_artifact_contents(tmp_path,nav_robot_model,monkeypatch):
    api=module();profile=candidate(tmp_path,nav_robot_model)
    receipt=api.prepare_admission(profile,nav_robot_model,'mujoco')
    def forbidden(*_args,**_kwargs):raise AssertionError('control service attempted artifact IO')
    monkeypatch.setattr(Path,'read_bytes',forbidden);monkeypatch.setattr(Path,'read_text',forbidden)
    assert receipt.check(profile,nav_robot_model,'mujoco')==(True,'')


def test_changed_proof_is_sticky_rejection_without_revalidation_or_retry(tmp_path,nav_robot_model):
    api=module();profile=candidate(tmp_path,nav_robot_model)
    receipt=api.prepare_admission(profile,nav_robot_model,'mujoco')
    file=tmp_path/'frames.json';old=file.read_bytes();file.write_bytes(b'changed')
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is False
    file.write_bytes(old)
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is False


def test_profile_or_engine_change_cannot_reuse_prepared_authority(tmp_path,nav_robot_model):
    api=module();profile=candidate(tmp_path,nav_robot_model)
    receipt=api.prepare_admission(profile,nav_robot_model,'mujoco')
    assert receipt.check(profile,nav_robot_model,'gazebo')[0] is False
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is False


def test_artifact_change_during_heavy_verification_is_not_cached_as_success(tmp_path,nav_robot_model):
    api=module();profile=candidate(tmp_path,nav_robot_model)
    def raced(*args):
        (tmp_path/'frames.json').write_bytes(b'changed during verification')
        return True,''
    receipt=api.prepare_admission(profile,nav_robot_model,'mujoco',checker=raced)
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is False


def test_repointed_result_alias_cannot_keep_old_prepared_authority(tmp_path,nav_robot_model):
    api=module();profile=candidate(tmp_path,nav_robot_model)
    alias=tmp_path/'result-alias.json';alias.symlink_to(tmp_path/'result.json')
    profile=replace(profile,native_evidence={'mujoco':dict(path=str(alias),sha256=sha(alias))})
    receipt=api.prepare_admission(profile,nav_robot_model,'mujoco')
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is True
    other=tmp_path/'other.json';other.write_text('{}')
    alias.unlink();alias.symlink_to(other)
    assert receipt.check(profile,nav_robot_model,'mujoco')[0] is False
