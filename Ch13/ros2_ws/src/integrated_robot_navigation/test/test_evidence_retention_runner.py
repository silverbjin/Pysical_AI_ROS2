"""Retention runs only after closed ownership, and cannot relabel a failed run."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def trial(path,*,closed=True):
    path.mkdir()
    (path/'result.json').write_text(json.dumps(dict(engine='mujoco',gate='G2',status='FAIL',
        errors=['actual support fault'],checks={'support':False})))
    (path/'teardown.json').write_text(json.dumps(dict(parent_reaped=closed,
        residual_live_pids=[] if closed else [123])))
    (path/'source_manifest.json').write_text('{"files":{"old":"hash"}}')
    (path/'frames.json').write_text(' '*4_200_000)
    return path


def test_closed_runner_rotates_old_raw_and_preserves_current_failure(tmp_path):
    old=trial(tmp_path/'old');current=trial(tmp_path/'current')
    original=(current/'result.json').read_bytes()
    result=runner.finalize_evidence_retention(current)
    assert result['applied'] is True
    assert not (old/'frames.json').exists() and (current/'frames.json').exists()
    assert (current/'result.json').read_bytes()==original


def test_unconfirmed_runtime_does_not_trigger_any_cleanup(tmp_path):
    old=trial(tmp_path/'old');current=trial(tmp_path/'current',closed=False)
    result=runner.finalize_evidence_retention(current)
    assert result['applied'] is False and 'cleanup' in result['reason']
    assert (old/'frames.json').exists() and (current/'frames.json').exists()


def test_failed_run_still_rotates_after_cleanup_and_keeps_original_exception(tmp_path,monkeypatch):
    old=trial(tmp_path/'old');current=trial(tmp_path/'current')
    def failed(_):raise RuntimeError('original support failure')
    monkeypatch.setattr(runner,'run',failed)
    with pytest.raises(RuntimeError,match='original support failure'):
        runner.run_with_retention(SimpleNamespace(output_dir=str(current)))
    assert not (old/'frames.json').exists()
    assert json.loads((current/'result.json').read_text())['status']=='FAIL'


def test_storage_error_cannot_pass_even_when_physical_checks_are_true(tmp_path):
    from verify_vision_13_4 import EvidenceRun
    from evidence_retention_13_5 import EvidenceBudget
    (tmp_path/'observations.cdr').write_bytes(b'123456789')
    with pytest.raises(RuntimeError,match='required checks'):
        with EvidenceRun(tmp_path,{'physical'}) as result:
            try:EvidenceBudget(tmp_path,raw_bytes=8).check()
            except RuntimeError as error:result.fail(str(error))
            result.artifact(tmp_path/'observations.cdr')
            result.finish({'physical':True})
    assert json.loads((tmp_path/'result.json').read_text())['status']=='FAIL'
