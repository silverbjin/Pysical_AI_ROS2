#!/usr/bin/env python3
"""Fresh serial verification, with independent fixture/semantic/safety verdicts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid

from verify_vision_13_4 import EvidenceRun, source_snapshot, verdict

CORE_GROUPS = frozenset({'build', 'pytest', 'colcon', 'colcon_result', 'installed_paths'} |
    {f'{kind}_{engine}' for engine in ('gazebo', 'mujoco') for kind in (
        'geometry', 'legacy', 'safety_images', 'safety_tf', 'safety_joints')})
OPTIONAL_GROUPS = frozenset({'yolo_smoke', 'yolo_gazebo', 'yolo_mujoco',
                             'tracking_gazebo', 'tracking_mujoco'})


def git_blob_sha256(repo, commit, path):
    data = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=repo)
    return hashlib.sha256(data).hexdigest()


def summarize(results, run_id):
    groups = {}
    try:
        valid_id = str(uuid.UUID(run_id)) == run_id
    except (ValueError, TypeError, AttributeError):
        valid_id = False
    for key in sorted(CORE_GROUPS | OPTIONAL_GROUPS):
        value = results.get(key)
        if value is None:
            groups[key] = dict(status='UNVERIFIED')
            continue
        good = (valid_id and value.get('batch_run_id') == run_id and value.get('group') == key
                and verdict(value, {'executed', 'verification'}) == 'PASS')
        groups[key] = dict(status='PASS' if good else 'FAIL',
            run_id=value.get('run_id'), evidence=value.get('artifact_root'),
            measurements=value.get('measurements', {}), errors=value.get('errors', []))
    status = ('FAIL' if any(groups[k]['status'] != 'PASS' for k in CORE_GROUPS) else
              'PARTIAL' if any(groups[k]['status'] != 'PASS' for k in OPTIONAL_GROUPS) else 'PASS')
    return dict(schema_version=1, run_id=run_id, status=status, groups=groups,
        outside_scope={key: 'UNVERIFIED' for key in (
            'GUI', 'real_robot', 'PPO_loaded_walking', 'MoveIt', 'physical_grasp', 'Nav2_approach')},
        note='Command success, native sensor geometry, recognition, tracking and physical grasp are distinct.')


def residual_pids(path):
    """Inspect only declared native geometry children; never signal these IDs."""
    path = Path(path)
    value = json.loads(path.read_text(encoding='utf-8'))
    if 'cleanup' not in value and 'phases' not in value:
        raise ValueError('native result has no owned cleanup record')
    found = {pid for item in value.get('cleanup', []) for pid in item['residual_live_pids']}
    for phase in value.get('phases', {}):
        if phase not in ('static', 'delay'):
            raise ValueError('unknown geometry child')
        found.update(residual_pids(path.parent/phase/'result.json'))
    return sorted(found)


def run_command(group, command, *, output, batch_run_id, cwd, kind='command', env=None,
                result_path=None):
    """Own this fresh command; never accept an older result or a zero-test run."""
    run = EvidenceRun(output, {'executed', 'verification'})
    with run:
        run.result.update(batch_run_id=batch_run_id, group=group, command=list(map(str, command)))
        log = run.root/'command.log'
        checks = dict(executed=False, verification=False)
        try:
            with log.open('w', encoding='utf-8') as stream:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                    stderr=subprocess.STDOUT, start_new_session=True)
                run.result['pid'] = process.pid
                run.save()
                try:
                    code = process.wait()
                except KeyboardInterrupt:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=45.)
                    except subprocess.TimeoutExpired:
                        run.fail('Interrupted command did not acknowledge shutdown; do not start another engine')
                    raise
            run.result['returncode'] = code
            checks['executed'] = code == 0
            text = log.read_text(encoding='utf-8')
            checks['verification'] = code == 0
            if kind in ('pytest', 'colcon_result'):
                pattern = r'(\d+) passed' if kind == 'pytest' else r'Summary: (\d+) tests, 0 errors, 0 failures, 0 skipped'
                counts = [int(v) for v in re.findall(pattern, text)]
                run.result['test_count'] = max(counts, default=0)
                checks['verification'] = checks['verification'] and run.result['test_count'] > 0
            if kind in ('native', 'legacy', 'smoke'):
                path = Path(result_path)
                if not path.is_file() or path.stat().st_mtime < run.result['started_at']:
                    raise RuntimeError('missing or stale result from this command')
                value = json.loads(path.read_text(encoding='utf-8'))
                if kind == 'native':
                    from run_vision_13_4 import required_checks
                    required = ({'static', 'delay'} if group.startswith('geometry_') else
                        required_checks('safety' if group.startswith('safety_') else
                                        'tracking' if group.startswith('tracking_') else 'yolo'))
                    run.result['residual_live_pids'] = residual_pids(path)
                    run.result['cleanup_confirmed'] = not run.result['residual_live_pids']
                    valid = (value['started_at'] >= run.result['started_at'] and
                        run.result['cleanup_confirmed'] and verdict(value, required) == 'PASS')
                elif kind == 'smoke':
                    required = {'actual_yolo', 'bus_class_5', 'weights_hash_verified',
                                'image_hash_verified', 'sdk_autoinstall_disabled'}
                    valid = (value['started_at'] >= run.result['started_at'] and
                        value.get('status') == 'PASS' and not value.get('errors') and
                        all(value['checks'].get(k) is True for k in required))
                else:
                    valid = value.get('status') == 'PASS' and value.get('runtime_shutdown') == 'PASS'
                    for native_log in path.parent.glob('*.log'):
                        if any(v in native_log.read_text(encoding='utf-8') for v in (
                                'Traceback', 'escalating to', 'process has died', 'failed to terminate')):
                            valid = False
                checks['verification'] = bool(checks['verification'] and valid)
                run.result['measurements'] = {k: value[k] for k in (
                    'geometry', 'recognition', 'tracking_metrics', 'phases', 'fault', 'versions',
                    'checks', 'runtime_shutdown', 'errors') if k in value}
                run.artifact(path)
        except Exception as exc:
            run.fail(repr(exc))
        finally:
            if log.is_file() and log.stat().st_size:
                run.artifact(log)
        try:
            run.finish(checks)
        except RuntimeError:
            pass
    return run.result


def environment(underlay, install=None):
    cleaned = os.environ.copy()
    for key in ('AMENT_PREFIX_PATH', 'CMAKE_PREFIX_PATH', 'COLCON_PREFIX_PATH',
                'PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'PKG_CONFIG_PATH'):
        cleaned.pop(key, None)
    sources = ['/opt/ros/jazzy/setup.bash', str(underlay)]
    if install is not None:
        sources.append(str(install/'setup.bash'))
    setup = ' && '.join('source '+shlex.quote(v) for v in sources)
    data = subprocess.check_output(['bash', '-c', setup+' && env -0'], env=cleaned)
    # Environment values stay in memory, not logs/artifacts (may contain secrets).
    result = dict(os.fsdecode(v).split('=', 1) for v in data.split(b'\0') if b'=' in v)
    result.update(ROS_DOMAIN_ID='157', MUJOCO_GL='egl', RCUTILS_COLORIZED_OUTPUT='0')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir')
    parser.add_argument('--weights', default='')
    parser.add_argument('--image', default='')
    parser.add_argument('--mujoco-underlay', default='/home/jinho/ch13_mujoco_ws/install/setup.bash')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    batch = str(uuid.uuid4())
    output = Path(args.output_dir or repo/'Ch13/evidence/section_13_4'/('final-'+batch)).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    (output/'summary.json').write_text(json.dumps(dict(status='RUNNING', run_id=batch))+'\n', encoding='utf-8')
    snapshot = source_snapshot(repo)
    (output/'source_snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
    ws = repo/'Ch13/ros2_ws'
    suffix = '13_4_verify_'+batch[:8]
    build, install, logs = [ws/(name+suffix) for name in ('build', 'install', 'log')]
    base = [sys.executable, '/usr/bin/colcon', '--log-base', str(logs)]
    packages = ['--packages-select', 'integrated_robot_interfaces', 'integrated_robot_vision',
                'integrated_robot_description', 'integrated_robot_runtime']
    env = None

    def execute(key, command, kind='command', result_path=None, cwd=repo):
        value = run_command(key, command, output=output/key, batch_run_id=batch, cwd=cwd,
                            env=env, kind=kind, result_path=result_path)
        results[key] = value
        (output/'summary.json').write_text(json.dumps(summarize(results, batch), indent=2)+'\n', encoding='utf-8')
        print(key+': '+value['status'], flush=True)
        if kind == 'native' and not value.get('cleanup_confirmed', False):
            raise RuntimeError('Native cleanup unconfirmed; refusing to start another engine')
        return value['status'] == 'PASS'

    try:
        env = environment(Path(args.mujoco_underlay))
        built = execute('build', base+['build', '--build-base', str(build), '--install-base', str(install)]
            +packages+['--cmake-args', '-DPython3_EXECUTABLE='+sys.executable], cwd=ws)
        if not built:
            return 1
        env = environment(Path(args.mujoco_underlay), install)
        path_code = '''import hashlib, importlib.util, json
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
prefix, repo = Path(PREFIX), Path(REPO)
rows = {}
for name in ('integrated_robot_runtime','integrated_robot_vision','integrated_robot_interfaces','integrated_robot_description'):
    share = Path(get_package_share_directory(name)).resolve()
    assert share.is_relative_to(prefix), (name, str(share))
    rows[name] = str(share)
    if name in ('integrated_robot_runtime','integrated_robot_vision'):
        installed = Path(importlib.util.find_spec(name).origin).resolve().parent
        assert installed.is_relative_to(prefix), str(installed)
        source = repo/'Ch13/ros2_ws/src'/name/name
        for path in source.glob('*.py'):
            assert path.read_bytes() == (installed/path.name).read_bytes(), str(path)
    if name == 'integrated_robot_description':
        source = repo/'Ch13/ros2_ws/src'/name
        for directory in ('launch','config','urdf','mujoco','worlds'):
            for path in (source/directory).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    assert path.read_bytes() == (share/path.relative_to(source)).read_bytes(), str(path)
print(json.dumps(rows, indent=2))
'''.replace('PREFIX', repr(str(install))).replace('REPO', repr(str(repo)))
        execute('installed_paths', [sys.executable, '-c', path_code])
        execute('pytest', [sys.executable, '-m', 'pytest', 'Ch13/tests',
            'Ch13/ros2_ws/src/integrated_robot_vision/test',
            'Ch13/ros2_ws/src/integrated_robot_runtime/test', '-q'], 'pytest')
        execute('colcon', base+['test', '--build-base', str(build), '--install-base', str(install),
            '--executor', 'sequential']+packages, cwd=ws)
        execute('colcon_result', [sys.executable, '/usr/bin/colcon', 'test-result',
            '--test-result-base', str(build), '--verbose'], 'colcon_result', cwd=ws)
        smoke = output/'yolo_smoke/native/result.json'
        execute('yolo_smoke', [sys.executable, 'Ch13/scripts/verify_yolo_13_4.py',
            '--weights', args.weights, '--image', args.image, '--output', str(smoke),
            '--annotation-dir', str(Path(args.weights).resolve().parent/'smoke_annotations')], 'smoke', smoke)
        for engine in ('gazebo', 'mujoco'):
            for scenario, fault in [('geometry', None), ('yolo', None), ('tracking', None),
                                    ('safety', 'images'), ('safety', 'tf'), ('safety', 'joints')]:
                key = (scenario+('_'+fault if fault else '')+'_'+engine)
                native = output/key/'native'
                command = [sys.executable, 'Ch13/scripts/run_vision_13_4.py', '--engine', engine,
                    '--scenario', scenario, '--detector-backend', 'yolo' if scenario == 'yolo' else 'color_fixture',
                    '--output-dir', str(native)]
                if scenario == 'yolo':
                    command += ['--weights-path', args.weights]
                if fault:
                    command += ['--fault', fault]
                execute(key, command, 'native', native/'result.json')
            native = output/('legacy_'+engine)/'native'
            execute('legacy_'+engine, [sys.executable, 'Ch13/scripts/run_architecture_13_3.py',
                '--engine', engine, '--output-dir', str(native)], 'legacy', native/'result.json')
    except KeyboardInterrupt:
        print('Interrupted; unexecuted groups remain UNVERIFIED', flush=True)
    except Exception as exc:
        print('Verification stopped: '+repr(exc), flush=True)
    finally:
        summary = summarize(results, batch)
        summary.update(verified_source_head=snapshot['head'], finished_at=time.time(),
                       build_prefix=str(build), install_prefix=str(install))
        (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(status=summary['status'], output=str(output), run_id=batch)), flush=True)
    return 1 if summary['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
