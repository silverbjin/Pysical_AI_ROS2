#!/usr/bin/env python3
"""Fail-closed evidence contracts. A file named result.json is not proof of PASS."""
import argparse
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path
from threading import RLock
import time
import uuid
import numpy as np


def source_snapshot(repo):
    """Working bytes, including uncommitted implementation, not just HEAD."""
    repo = Path(repo).resolve()
    roots = [repo/'Ch13/scripts', repo/'Ch13/tests'] + [repo/'Ch13/ros2_ws/src'/name for name in (
        'integrated_robot_description', 'integrated_robot_interfaces',
        'integrated_robot_runtime', 'integrated_robot_vision')]
    files = {}
    for root in roots:
        for path in sorted(root.rglob('*')):
            if (path.is_file() and not any(v in path.parts for v in ('__pycache__', '.pytest_cache'))
                    and path.suffix not in ('.pyc', '.pyo')):
                files[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, capture_output=True, text=True)
    dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=repo,
                           capture_output=True, text=True)
    return dict(head=git.stdout.strip() if git.returncode == 0 else 'UNAVAILABLE', files=files,
                dirty_paths=dirty.stdout.splitlines() if dirty.returncode == 0 else ['UNAVAILABLE'])


def tracking_summary(commands, initial_errors, final_errors, *, elapsed,
                     measured_velocities=None, measured_positions=None):
    """Audit actual dispatched commands, never infer rate/speed from status ticks."""
    checks = dict(five_second_tracking=False, pixel_error_reduction=False,
                  joint_limits=False, velocity_limits=False, command_rate=False)
    result = dict(checks=checks, elapsed_wall_s=elapsed, command_count=len(commands), reduction=None)
    try:
        first, last = np.asarray(initial_errors, float), np.asarray(final_errors, float)
        if (len(first) >= 3 and len(last) >= 3 and np.isfinite(first).all()
                and np.isfinite(last).all() and np.min(first) >= 0 and np.min(last) >= 0
                and np.median(first) > 1.):
            result['initial_median_px'], result['final_median_px'] = float(np.median(first)), float(np.median(last))
            result['reduction'] = float(1.-np.median(last)/np.median(first))
            checks['pixel_error_reduction'] = result['reduction'] >= .2
        if len(commands) < 2:
            return result
        q = np.array([v['positions'] for v in commands], float)
        measured = np.array([v['measured_positions'] for v in commands], float)
        reference = np.array([v['activation_reference'] for v in commands], float)
        dispatch = np.array([v['dispatched_monotonic'] for v in commands], float)
        horizons = np.array([v['horizon_s'] for v in commands], float)
        names = ['arm_joint_'+str(j) for j in range(1, 7)]
        valid = (q.shape == measured.shape == reference.shape == (len(commands), 6)
                 and all(v['joint_names'] == names for v in commands)
                 and all(np.isfinite(v).all() for v in (q, measured, reference, dispatch, horizons))
                 and np.all(horizons == .2)
                 and len({v['goal_uuid'] for v in commands}) == len(commands))
        if not valid:
            return result
        checks['five_second_tracking'] = bool(math.isfinite(elapsed) and elapsed >= 5.
                                             and dispatch[-1]-dispatch[0] >= 4.5)
        checks['joint_limits'] = bool(np.all(np.abs(q[:, [0, 4]]) <= .04+1e-9)
            and np.all(q[:, [1, 2, 3, 5]] == reference[:, [1, 2, 3, 5]]))
        checks['velocity_limits'] = bool(np.all(np.abs(q-measured) <= .1*.2+1e-9))
        checks['command_rate'] = bool(np.all(np.diff(dispatch) >= .2-1e-6))
        result['minimum_dispatch_interval_s'] = float(np.min(np.diff(dispatch)))
        for label, values, check, limit in (
                ('measured_max_speed_rad_s', measured_velocities, 'velocity_limits', .1),
                ('measured_max_angle_rad', measured_positions, 'joint_limits', .04)):
            values = np.asarray(values, float)
            usable = (values.ndim == 2 and values.shape[1] == 6 and len(values) > 0
                      and np.isfinite(values).all())
            maximum = float(np.max(np.abs(values[:, [0, 4]]))) if usable else None
            result[label] = maximum
            checks[check] = bool(checks[check] and usable and maximum <= limit+1e-6)
    except (KeyError, ValueError, TypeError, IndexError):
        pass
    return result


def visible_surface_point(u, v, intrinsics, optical_in_odom, *, fixture_y=0.):
    """Intersection with declared native fixture front x=.98, not COM x=1.

    Camera pose is the calibrated capture-time observation. This is a physical
    depth/plane consistency test, not independent ground truth for every TF DOF.
    Independent URDF/native camera parity is tested separately.
    """
    fx, fy, cx, cy = intrinsics
    pose = np.asarray(optical_in_odom, dtype=float)
    if (pose.shape != (4, 4) or not np.isfinite(pose).all()
            or not all(math.isfinite(value) for value in (u, v, fx, fy, cx, cy, fixture_y))
            or min(fx, fy) <= 0):
        raise ValueError('finite calibrated camera pose required')
    ray = pose[:3, :3] @ np.array([(u-cx)/fx, (v-cy)/fy, 1.])
    if abs(ray[0]) < 1e-9:
        return None
    distance = (.98-pose[0, 3])/ray[0]
    point = pose[:3, 3]+distance*ray
    if distance <= 0 or abs(point[1]-fixture_y) > .25+1e-9 or not .52-1e-9 <= point[2] <= .92+1e-9:
        return None
    return point


def rms_error(errors):
    values = np.asarray(errors, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or not values.size or not np.isfinite(values).all():
        raise ValueError('nonempty finite Nx3 measured errors required')
    return float(np.sqrt(np.mean(np.sum(values**2, axis=1))))


def geometry_summary(samples, limit):
    if not math.isfinite(limit) or limit <= 0:
        raise ValueError('positive finite RMS acceptance limit required')
    count = len(samples)
    unique = len({v['capture_ns'] for v in samples})
    rms = rms_error([v['error'] for v in samples]) if samples else None
    latest = (rms_error([v['latest_tf_error'] for v in samples]) if samples and all(
        'latest_tf_error' in v for v in samples) else None)
    return dict(valid_samples=count, unique_captures=unique, rms_m=rms,
                rms_limit_m=limit, required_samples=30, unique_timestamps=unique == count,
                latest_tf_diagnostic_rms_m=latest,
                accepted=unique >= 30 and unique == count and rms is not None and rms <= limit)


def tf_contract_single_owners(graph, observed_parents, expected_parents):
    """Jazzy lacks per-message GID: graph + complete model/source contract inference.

    NOT a claim to have attributed packets to DDS writers. Unknown publishers,
    missing links, duplicate parents, or a model/observed parent mismatch fail.
    """
    return bool(expected_parents) and (
        sorted(graph.get('/tf', [])) == ['native_pose_adapter', 'robot_state_publisher']
        and graph.get('/tf_static', []) == ['robot_state_publisher']
        and set(observed_parents) == set(expected_parents)
        and all(observed_parents[child] == {parent} for child, parent in expected_parents.items()))


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verdict(result: dict, required: set[str]) -> str:
    try:
        if (not required or result['schema_version'] != 1
                or result['status'] not in ('COMPLETE', 'PASS') or result['errors']
                or str(uuid.UUID(result['run_id'])) != result['run_id']
                or result['run_id'] != result['expected_run_id']
                or not all(type(result['checks'][key]) is bool and result['checks'][key]
                           for key in required)):
            return 'FAIL'
        times = [result[key] for key in ('invocation_started_at', 'started_at', 'finished_at')]
        if (not all(math.isfinite(v) and v > 0 for v in times)
                or not times[0] <= times[1] <= times[2]):
            return 'FAIL'
        root = Path(result['artifact_root']).resolve(strict=True)
        if not result['artifacts']:
            return 'FAIL'
        for artifact in result['artifacts']:
            path = (root/artifact['path']).resolve(strict=True)
            if (not path.is_relative_to(root) or not path.is_file() or artifact['size'] <= 0
                    or path.stat().st_size != artifact['size']
                    or file_digest(path) != artifact['sha256']):
                return 'FAIL'
        return 'PASS'
    except (KeyError, TypeError, ValueError, OSError, OverflowError):
        return 'FAIL'


class EvidenceRun:
    def __init__(self, output, required):
        self.root = Path(output).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.required = set(required)
        self.lock = RLock()
        self.run_id = str(uuid.uuid4())
        now = time.time()
        self.result = dict(schema_version=1, run_id=self.run_id, expected_run_id=self.run_id,
                           invocation_started_at=now, started_at=now, status='RUNNING',
                           checks={}, errors=[], artifact_root=str(self.root), artifacts=[],
                           required_checks=sorted(self.required))
        self.save()  # BEFORE constructing any engine/node/model/worker

    def save(self):
        with self.lock:
            temporary = self.root/('result.'+self.run_id+'.tmp')
            try:
                with temporary.open('w', encoding='utf-8') as stream:
                    json.dump(self.result, stream, indent=2, allow_nan=False)
                    stream.write('\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(self.root/'result.json')
            finally:
                temporary.unlink(missing_ok=True)

    def __enter__(self):
        return self

    def fail(self, message):
        with self.lock:
            self.result['errors'].append(str(message))
            self.result['status'] = 'FAIL'
            self.save()

    def artifact(self, path):
        path = Path(path).resolve(strict=True)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('evidence artifact must be inside this invocation output')
        with self.lock:
            self.result['artifacts'].append(dict(path=str(path.relative_to(self.root)),
                size=path.stat().st_size, sha256=file_digest(path)))

    def finish(self, checks):
        with self.lock:
            self.result.update(checks=dict(checks), finished_at=time.time(), status='COMPLETE')
            self.result['status'] = verdict(self.result, self.required)
            self.save()
            if self.result['status'] != 'PASS':
                raise RuntimeError('required checks/artifacts incomplete, stale, or failed')

    def __exit__(self, kind, exception, traceback):
        if exception is not None:
            self.fail(repr(exception))
        elif self.result['status'] == 'RUNNING':
            self.fail('verification ended without explicit completion')
            raise RuntimeError('verification incomplete')
        self.result['finished_at'] = time.time()
        self.save()
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', required=True)
    parser.add_argument('--run-id', required=True, help='Expected ID from THIS invocation, not an old file')
    parser.add_argument('--started-after', required=True, type=float)
    args = parser.parse_args()
    try:
        result = json.loads(Path(args.result).read_text(encoding='utf-8'))
        result['expected_run_id'] = args.run_id
        result['invocation_started_at'] = args.started_after
        status = verdict(result, set(result['required_checks']))
    except (OSError, ValueError, KeyError, TypeError):
        status = 'FAIL'
    print(status)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
