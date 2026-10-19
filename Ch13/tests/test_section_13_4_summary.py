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


def test_fresh_install_audit_covers_five_packages_and_camera_source_binary_identity():
    from ament_index_python.packages import get_package_prefix
    from verify_all_13_4 import audit_installed_paths
    prefix = Path(get_package_prefix('integrated_robot_camera')).parent
    repo = Path(__file__).resolve().parents[2]
    # conftest intentionally puts source modules first. Do not weaken the audit
    # to accept that; execute the installed audit in a fresh interpreter instead.
    with pytest.raises(RuntimeError, match='stale Python module'):
        audit_installed_paths(prefix, repo)
    rows = json.loads(subprocess.check_output([sys.executable,
        str(repo/'Ch13/scripts/verify_all_13_4.py'), '--audit-install-prefix', str(prefix)],
        text=True, timeout=30.))
    assert set(rows) == {'integrated_robot_camera', 'integrated_robot_description',
                         'integrated_robot_interfaces', 'integrated_robot_runtime', 'integrated_robot_vision'}
    camera = rows['integrated_robot_camera']
    assert camera['source_hashes']['src/snapshot_camera_plugin.cpp'] == hashlib.sha256(
        (repo/'Ch13/ros2_ws/src/integrated_robot_camera/src/snapshot_camera_plugin.cpp').read_bytes()).hexdigest()
    assert len(camera['library_sha256']) == 64
    assert Path(camera['library_path']).is_relative_to(prefix)
    assert camera['license_verified'] and camera['plugin_xml_verified']


def test_batch_native_command_forwards_explicit_backend_and_rate():
    from types import SimpleNamespace
    from verify_all_13_4 import native_trial_command
    args = SimpleNamespace(weights='/local/weights.pt', vision_camera_backend='snapshot', inference_rate_hz=15.)
    for engine in ('mujoco', 'gazebo'):
        command = native_trial_command(args, engine, 'tracking', Path('/tmp/native-proof'))
        assert command[command.index('--vision-camera-backend')+1] == 'snapshot'
        assert command[command.index('--inference-rate-hz')+1] == '15.0'
        assert command[command.index('--engine')+1] == engine


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


def test_raw_native_model_whitespace_is_preserved_without_disabling_source_checks(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    evidence, source = tmp_path/'evidence', tmp_path/'src'
    evidence.mkdir()
    source.mkdir()
    attrs = Path(__file__).resolve().parents[1]/'evidence/section_13_4/.gitattributes'
    (evidence/'.gitattributes').write_bytes(attrs.read_bytes())
    for directory in (evidence, source):
        (directory/'model.xml').write_bytes(b'<mujoco>\n  \n</mujoco>\n')
    subprocess.run(['git', 'add', 'evidence', 'src'], cwd=tmp_path, check=True)
    raw = subprocess.run(['git', 'diff', '--cached', '--check', '--', 'evidence'],
                         cwd=tmp_path, capture_output=True, text=True)
    assert raw.returncode == 0, 'native generated model bytes must not be trimmed after hashing: '+raw.stdout
    ordinary = subprocess.run(['git', 'diff', '--cached', '--check', '--', 'src'],
                              cwd=tmp_path, capture_output=True, text=True)
    assert ordinary.returncode != 0  # authored source whitespace remains checked
