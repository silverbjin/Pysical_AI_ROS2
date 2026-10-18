"""A smoke image or fixture PASS cannot stand in for a fresh engine feature test."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_vision_13_4 import EvidenceRun
from verify_all_13_4 import CORE_GROUPS, OPTIONAL_GROUPS, summarize, git_blob_sha256, run_command, residual_pids


def proof(tmp_path, batch, key):
    with EvidenceRun(tmp_path/key, {'executed', 'verification'}) as run:
        run.result.update(batch_run_id=batch, group=key)
        path = run.root/'observed.txt'
        path.write_text('contract test artifact, not native evidence')
        run.artifact(path)
        run.finish(dict(executed=True, verification=True))
    return run.result


def test_fixture_does_not_imply_yolo_or_tracking_success(tmp_path):
    batch = str(uuid.uuid4())
    results = {key: proof(tmp_path, batch, key) for key in CORE_GROUPS}
    value = summarize(results, batch)
    assert value['status'] == 'PARTIAL'
    assert value['groups']['yolo_mujoco']['status'] == 'UNVERIFIED'
    assert all(v == 'UNVERIFIED' for v in value['outside_scope'].values())
    results.update({key: proof(tmp_path, batch, key) for key in OPTIONAL_GROUPS})
    assert summarize(results, batch)['status'] == 'PASS'
    assert summarize({}, batch)['status'] == 'FAIL'
    assert summarize({'yolo_smoke': results['yolo_smoke']}, batch)['status'] == 'FAIL'


@pytest.mark.parametrize('damage', ['old_batch', 'missing', 'error', 'false', 'corrupt', 'old_time'])
def test_false_pass_or_missing_core_group_fails(tmp_path, damage):
    batch = str(uuid.uuid4())
    results = {key: proof(tmp_path, batch, key) for key in CORE_GROUPS}
    key = sorted(CORE_GROUPS)[0]
    if damage == 'old_batch':
        results[key]['batch_run_id'] = str(uuid.uuid4())
    elif damage == 'missing':
        del results[key]
    elif damage == 'error':
        results[key]['errors'].append('worker crashed despite PASS label')
    elif damage == 'false':
        results[key]['checks']['verification'] = False
    elif damage == 'corrupt':
        (Path(results[key]['artifact_root'])/'observed.txt').write_text('changed')
    elif damage == 'old_time':
        results[key]['finished_at'] = 1.
    assert summarize(results, batch)['status'] == 'FAIL'


def test_source_manifest_uses_commit_blob_not_crlf_working_bytes(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    source = tmp_path/'source.py'
    source.write_bytes(b'first\nsecond\n')
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'add', 'source.py'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Ch13 test', '-c', 'user.email=test@example.invalid',
                    'commit', '-qm', 'temporary source fixture'], cwd=tmp_path, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    source.write_bytes(b'first\r\nsecond\r\n')
    assert git_blob_sha256(tmp_path, commit, 'source.py') == hashlib.sha256(b'first\nsecond\n').hexdigest()


def test_actual_zero_test_command_is_not_a_verification_pass(tmp_path):
    value = run_command('pytest', [sys.executable, '-c', 'print("0 passed")'],
        output=tmp_path/'zero', batch_run_id=str(uuid.uuid4()), cwd=tmp_path, kind='pytest')
    assert value['status'] == 'FAIL' and value['test_count'] == 0


def test_malformed_batch_and_nested_geometry_residuals_cannot_continue(tmp_path):
    assert summarize({}, 'not-a-uuid')['status'] == 'FAIL'
    (tmp_path/'static').mkdir()
    (tmp_path/'static/result.json').write_text(json.dumps({'cleanup': [{'residual_live_pids': [123]}]}))
    path = tmp_path/'result.json'
    path.write_text(json.dumps({'phases': {'static': 'FAIL'}, 'cleanup': []}))
    assert residual_pids(path) == [123]


def test_native_artifact_bytes_survive_git_checkout_with_windows_line_endings(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    attrs = Path(__file__).resolve().parents[1]/'evidence/section_13_4/.gitattributes'
    (tmp_path/'.gitattributes').write_bytes(attrs.read_bytes())
    expected = {'engine.log': b'native engine output\n', 'observations.json': b'{"actual":true}\n'}
    for name, value in expected.items():
        (tmp_path/name).write_bytes(value)
    subprocess.run(['git', '-c', 'core.autocrlf=true', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Ch13 test', '-c', 'user.email=test@example.invalid',
                    'commit', '-qm', 'temporary evidence fixture'], cwd=tmp_path, check=True)
    restored = tmp_path/'restored'
    subprocess.run(['git', '-c', 'core.autocrlf=true', 'checkout-index', '--all',
                    '--prefix='+str(restored)+'/'], cwd=tmp_path, check=True)
    for name, value in expected.items():
        assert (restored/name).read_bytes() == value, 'checkout must not corrupt recorded artifact SHA-256'
