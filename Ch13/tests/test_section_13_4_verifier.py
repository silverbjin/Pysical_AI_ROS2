"""A fresh invocation and complete measured evidence are mandatory for PASS."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import uuid

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))
from verify_vision_13_4 import EvidenceRun, verdict
from verify_vision_13_4 import visible_surface_point, rms_error
from verify_vision_13_4 import geometry_summary
import numpy as np


def test_source_snapshot_hashes_dirty_code_but_not_previous_build_outputs(tmp_path):
    from verify_vision_13_4 import source_snapshot
    source = tmp_path/'Ch13/ros2_ws/src/integrated_robot_vision/urdf/camera.xacro'
    source.parent.mkdir(parents=True)
    source.write_text('<robot/>')
    generated = tmp_path/'Ch13/ros2_ws/build13_4/test.py'
    generated.parent.mkdir(parents=True)
    generated.write_text('old generated result')
    first = source_snapshot(tmp_path)
    assert first['files'] == {source.relative_to(tmp_path).as_posix(): hashlib.sha256(source.read_bytes()).hexdigest()}
    source.write_text('<robot name="changed"/>')
    assert source_snapshot(tmp_path)['files'] != first['files']


def test_camera_cpp_is_in_source_inventory_and_changes_its_hash(tmp_path):
    from verify_vision_13_4 import source_snapshot
    source = tmp_path/'Ch13/ros2_ws/src/integrated_robot_camera/src/snapshot_camera_plugin.cpp'
    source.parent.mkdir(parents=True)
    source.write_text('first camera source')
    key = source.relative_to(tmp_path).as_posix()
    first = source_snapshot(tmp_path)
    assert first['files'][key] == hashlib.sha256(source.read_bytes()).hexdigest()
    source.write_text('changed camera source')
    assert source_snapshot(tmp_path)['files'][key] != first['files'][key]


def test_tracking_metrics_require_real_duration_commands_and_error_reduction():
    from verify_vision_13_4 import tracking_summary
    commands = [dict(goal_uuid=str(i), joint_names=['arm_joint_'+str(j) for j in range(1, 7)],
                     positions=[.01, 0., 0., 0., .01, 0.], measured_positions=[0.]*6,
                     activation_reference=[0.]*6, dispatched_monotonic=10.+i*.21,
                     horizon_s=.2) for i in range(25)]
    value = tracking_summary(commands, [10., 11., 9.], [6., 7., 8.], elapsed=5.2,
                             measured_velocities=np.zeros((10, 6)), measured_positions=np.zeros((10, 6)))
    assert all(value['checks'].values())
    assert value['reduction'] == pytest.approx(.3)
    assert not all(tracking_summary([], [10.], [5.], elapsed=6.)['checks'].values())
    assert not tracking_summary(commands, [10.]*3, [9.]*3, elapsed=6.)['checks']['pixel_error_reduction']
    assert not tracking_summary(commands, [10.]*3, [5.]*3, elapsed=4.)['checks']['five_second_tracking']
    commands[1]['dispatched_monotonic'] = 10.1
    assert not tracking_summary(commands, [10.]*3, [5.]*3, elapsed=6.)['checks']['command_rate']
    commands[1]['positions'][2] = .001
    assert not tracking_summary(commands, [10.]*3, [5.]*3, elapsed=6.)['checks']['joint_limits']
    commands[1]['positions'][0] = .03
    assert not tracking_summary(commands, [10.]*3, [5.]*3, elapsed=6.)['checks']['velocity_limits']
    commands[1]['positions'][0] = float('nan')
    assert not all(tracking_summary(commands, [10.]*3, [5.]*3, elapsed=6.)['checks'].values())


def test_tracking_measured_overspeed_or_excursion_cannot_hide_behind_safe_commands():
    from verify_vision_13_4 import tracking_summary
    commands = [dict(goal_uuid=str(i), joint_names=['arm_joint_'+str(j) for j in range(1, 7)],
                     positions=[0.]*6, measured_positions=[0.]*6, activation_reference=[0.]*6,
                     dispatched_monotonic=10.+i*.21, horizon_s=.2) for i in range(25)]
    kwargs = dict(elapsed=5.2, measured_velocities=np.zeros((10, 6)), measured_positions=np.zeros((10, 6)))
    assert all(tracking_summary(commands, [10.]*3, [5.]*3, **kwargs)['checks'].values())
    kwargs['measured_velocities'][0, 0] = .11
    assert not tracking_summary(commands, [10.]*3, [5.]*3, **kwargs)['checks']['velocity_limits']
    kwargs['measured_positions'][0, 4] = .041
    assert not tracking_summary(commands, [10.]*3, [5.]*3, **kwargs)['checks']['joint_limits']


def completed(tmp_path):
    artifact = tmp_path/'observations.txt'
    artifact.write_text('real observation placeholder for verifier contract test')
    identifier = str(uuid.uuid4())
    return dict(schema_version=1, run_id=identifier, expected_run_id=identifier,
                invocation_started_at=10., started_at=10., finished_at=11., status='COMPLETE',
                checks={'sensor': True, 'geometry': True}, errors=[], artifact_root=str(tmp_path),
                artifacts=[dict(path='observations.txt', size=artifact.stat().st_size,
                                sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())])


def test_complete_current_evidence_passes(tmp_path):
    assert verdict(completed(tmp_path), {'sensor', 'geometry'}) == 'PASS'


def test_snapshot_result_requires_loaded_library(tmp_path):
    from run_vision_13_4 import required_checks
    required = required_checks('tracking', engine='mujoco', camera_backend='snapshot')
    assert 'camera_backend_loaded' in required
    assert 'camera_backend_loaded' not in required_checks('tracking')
    assert 'camera_backend_loaded' not in required_checks('tracking', engine='gazebo')
    value = completed(tmp_path)
    value['checks'] = {key: True for key in required - {'camera_backend_loaded'}}
    assert verdict(value, required) == 'FAIL'
    value['checks']['camera_backend_loaded'] = True
    assert verdict(value, required) == 'FAIL'  # truthy check alone cannot invent backend provenance


def test_snapshot_metadata_must_match_its_hashed_artifact_and_prefix(tmp_path):
    import os
    value = completed(tmp_path)
    required = {'camera_backend_loaded'}
    value.update(engine='mujoco', vision_camera_backend='snapshot', checks={'camera_backend_loaded': True})
    prefix = tmp_path/'package'
    audit = dict(class_id='integrated_robot_camera/SnapshotCameraPlugin', native_pid=os.getpid(),
        package_prefix=str(prefix), library_path=str(prefix/'lib/libsnapshot_camera_plugin.so'),
        library_sha256='a'*64)
    path = tmp_path/'camera_backend.json'
    path.write_text(json.dumps(audit))  # verifier contract fixture, not native evidence
    value['camera_backend_audit'] = audit
    value['artifacts'].append(dict(path=path.name, size=path.stat().st_size,
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assert verdict(value, required) == 'PASS'
    for field, bad in [('native_pid', 0), ('class_id', 'upstream'),
                       ('package_prefix', '/unrelated/prefix'), ('library_sha256', 'broken')]:
        damaged = deepcopy(value)
        damaged['camera_backend_audit'][field] = bad
        assert verdict(damaged, required) == 'FAIL'
    value['vision_camera_backend'] = 'upstream'
    assert verdict(value, required) == 'FAIL'


@pytest.mark.parametrize('defect', ['missing', 'false', 'not_bool', 'errors', 'running', 'old_id',
                                   'old_time', 'no_finish', 'no_artifact', 'empty_artifact',
                                   'corrupt_artifact', 'traversal', 'no_required', 'nan_time'])
def test_incomplete_stale_or_unmeasured_evidence_fails(tmp_path, defect):
    value = completed(tmp_path)
    required = {'sensor', 'geometry'}
    if defect == 'missing':
        del value['checks']['geometry']
    elif defect == 'false':
        value['checks']['geometry'] = False
    elif defect == 'not_bool':
        value['checks']['geometry'] = 1
    elif defect == 'errors':
        value['errors'].append('constructor, worker, finish, process death or deadline failed')
    elif defect == 'running':
        value['status'] = 'RUNNING'
    elif defect == 'old_id':
        value['run_id'] = str(uuid.uuid4())
    elif defect == 'old_time':
        value['started_at'] = 9.
    elif defect == 'no_finish':
        del value['finished_at']
    elif defect == 'no_artifact':
        (tmp_path/'observations.txt').unlink()
    elif defect == 'empty_artifact':
        value['artifacts'] = []
    elif defect == 'corrupt_artifact':
        (tmp_path/'observations.txt').write_text('changed evidence')
    elif defect == 'traversal':
        value['artifacts'][0]['path'] = '../observations.txt'
    elif defect == 'no_required':
        required = set()
    elif defect == 'nan_time':
        value['finished_at'] = float('nan')
    assert verdict(value, required) == 'FAIL'


@pytest.mark.parametrize('failure', ['constructor', 'finish', 'death'])
def test_actual_failing_process_never_reuses_old_pass(tmp_path, failure):
    previous = completed(tmp_path)
    previous['status'] = 'PASS'
    (tmp_path/'result.json').write_text(json.dumps(previous))
    code = ('import os,sys; from verify_vision_13_4 import EvidenceRun; '
            f'run=EvidenceRun({str(tmp_path)!r}, {{"sensor"}});\n'
            'with run:\n'
            + (' raise RuntimeError("resource constructor failed")\n' if failure == 'constructor'
               else ' run.finish({"sensor":True})\n' if failure == 'finish'
               else ' os._exit(3)\n'))
    execution = subprocess.run([sys.executable, '-c', code], cwd=SCRIPTS,
                               capture_output=True, text=True, timeout=5.)
    assert execution.returncode != 0
    current = json.loads((tmp_path/'result.json').read_text())
    assert current['run_id'] != previous['run_id']
    assert verdict(current, {'sensor'}) == 'FAIL'


def test_worker_failure_cannot_be_overwritten_by_later_finish(tmp_path):
    with EvidenceRun(tmp_path, {'sensor'}) as run:
        worker = threading.Thread(target=lambda: run.fail('worker exception'))
        worker.start()
        worker.join()
        artifact = tmp_path/'actual.txt'
        artifact.write_text('measured')
        run.artifact(artifact)
        with pytest.raises(RuntimeError):
            run.finish({'sensor': True})
    assert json.loads((tmp_path/'result.json').read_text())['status'] == 'FAIL'


def test_normal_completion_checks_artifact_and_fresh_invocation(tmp_path):
    with EvidenceRun(tmp_path, {'sensor'}) as run:
        identifier = run.run_id
        artifact = tmp_path/'actual.txt'
        artifact.write_text('measured')
        run.artifact(artifact)
        run.finish({'sensor': True})
    result = json.loads((tmp_path/'result.json').read_text())
    assert result['run_id'] == identifier and result['status'] == 'PASS'
    result['status'] = 'COMPLETE'
    assert verdict(result, {'sensor'}) == 'PASS'


def test_physical_surface_ground_truth_is_ray_intersection_not_box_center():
    pose = np.eye(4)
    # Optical +z looks along world +x; optical +x maps to world -y.
    pose[:3, :3] = [[0., 0., 1.], [-1., 0., 0.], [0., -1., 0.]]
    pose[:3, 3] = [0., 0., .72]
    point = visible_surface_point(170., 120., (277., 277., 160., 120.), pose)
    np.testing.assert_allclose(point, [.98, -.98*10/277., .72])
    assert point[0] != 1.  # center x is NOT the visible front surface x=.98
    assert rms_error([[0., 0., .01], [0., 0., -.01]]) == pytest.approx(.01)
    assert visible_surface_point(1000., 120., (277., 277., 160., 120.), pose) is None
    assert visible_surface_point(160., 120., (277., 277., 160., 120.), np.eye(4)) is None
    with pytest.raises(ValueError):
        rms_error([])
    with pytest.raises(ValueError):
        rms_error([[float('nan'), 0., 0.]])


def test_partial_geometry_is_preserved_but_never_zero_error_or_sufficient_samples():
    empty = geometry_summary([], .03)
    assert empty['rms_m'] is None and empty['valid_samples'] == 0 and not empty['accepted']
    samples = [dict(capture_ns=index+1, error=[.001, 0., 0.]) for index in range(30)]
    partial = geometry_summary(samples[:3], .03)
    assert partial['valid_samples'] == 3 and partial['rms_m'] == pytest.approx(.001)
    assert not partial['accepted']
    complete = geometry_summary(samples, .03)
    assert complete['accepted'] and complete['latest_tf_diagnostic_rms_m'] is None
    assert not geometry_summary(samples+[deepcopy(samples[0])], .03)['accepted']
