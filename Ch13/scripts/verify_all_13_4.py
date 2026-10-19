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

from verify_vision_13_4 import EvidenceRun, source_snapshot, verdict, file_digest

PACKAGES = ('integrated_robot_interfaces', 'integrated_robot_vision',
            'integrated_robot_description', 'integrated_robot_runtime', 'integrated_robot_camera')

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
                result_path=None, camera_backend='upstream'):
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
                    engine = group.rsplit('_', 1)[-1]
                    required = ({'static', 'delay'} if group.startswith('geometry_') else
                        required_checks('safety' if group.startswith('safety_') else
                                        'tracking' if group.startswith('tracking_') else 'yolo',
                                        engine=engine, camera_backend=camera_backend))
                    run.result['residual_live_pids'] = residual_pids(path)
                    run.result['cleanup_confirmed'] = not run.result['residual_live_pids']
                    valid = (value['started_at'] >= run.result['started_at'] and
                        run.result['cleanup_confirmed'] and verdict(value, required) == 'PASS')
                    if group.startswith('geometry_'):
                        for phase in ('static', 'delay'):
                            child = json.loads((path.parent/phase/'result.json').read_text())
                            valid = valid and verdict(child, required_checks(phase, engine=engine,
                                camera_backend=camera_backend)) == 'PASS'
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


def audit_installed_paths(prefix, repo):
    """Compare installed bytes and generated C++ build manifest with this source."""
    import importlib.util
    from ament_index_python.packages import get_package_share_directory, get_package_prefix
    prefix, repo = Path(prefix).resolve(), Path(repo).resolve()
    rows = {}
    for name in PACKAGES:
        share = Path(get_package_share_directory(name)).resolve()
        package_prefix = Path(get_package_prefix(name)).resolve()
        if not share.is_relative_to(prefix) or not package_prefix.is_relative_to(prefix):
            raise RuntimeError('stale installed package prefix: '+name)
        source = repo/'Ch13/ros2_ws/src'/name
        row = rows[name] = dict(share=str(share))
        if name in ('integrated_robot_runtime', 'integrated_robot_vision'):
            installed = Path(importlib.util.find_spec(name).origin).resolve().parent
            if not installed.is_relative_to(prefix):
                raise RuntimeError('stale Python module: '+name)
            for path in (source/name).glob('*.py'):
                if path.read_bytes() != (installed/path.name).read_bytes():
                    raise RuntimeError('installed Python bytes differ: '+str(path))
            for executable in (package_prefix/'lib'/name).iterdir():
                if executable.is_file() and executable.read_bytes().startswith(b'#!'):
                    if executable.read_bytes().splitlines()[0] != ('#!'+sys.executable).encode():
                        raise RuntimeError('console interpreter does not match venv: '+str(executable))
            row['python_source_verified'] = True
        for directory in (('launch', 'config', 'urdf', 'mujoco', 'worlds')
                          if name == 'integrated_robot_description' else
                          ('launch', 'config') if name in ('integrated_robot_runtime', 'integrated_robot_vision') else ()):
            for path in (source/directory).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    if path.read_bytes() != (share/path.relative_to(source)).read_bytes():
                        raise RuntimeError('installed share bytes differ: '+str(path))
        if name == 'integrated_robot_camera':
            hashes = json.loads((share/'source_manifest.json').read_text())
            for relative, digest in hashes.items():
                path = (source/relative).resolve(strict=True)
                if not path.is_relative_to(source.resolve()) or file_digest(path) != digest:
                    raise RuntimeError('C++ source differs from configured build: '+relative)
            for required in ('src/snapshot_camera_plugin.cpp', 'src/snapshot_mailbox.cpp',
                             'integrated_robot_camera_plugins.xml', 'LICENSE'):
                if required not in hashes:
                    raise RuntimeError('camera build source manifest incomplete')
            for filename in ('LICENSE', 'integrated_robot_camera_plugins.xml', 'REUSE_MANIFEST.md'):
                if (source/filename).read_bytes() != (share/filename).read_bytes():
                    raise RuntimeError('installed camera metadata differs: '+filename)
            from run_vision_13_4 import camera_launch_module
            row.update(camera_launch_module().probe_snapshot_plugin(package_prefix))
            mailbox = package_prefix/'lib/libsnapshot_mailbox.so'
            if not mailbox.resolve(strict=True).is_relative_to(package_prefix):
                raise RuntimeError('mailbox library resolves outside package prefix')
            row.update(mailbox_library_path=str(mailbox.resolve(strict=True)),
                       mailbox_library_sha256=file_digest(mailbox))
            row.update(source_hashes=hashes, license_verified=True, plugin_xml_verified=True)
    return rows


def native_trial_command(args, engine, scenario, output, fault=None):
    command = [sys.executable, 'Ch13/scripts/run_vision_13_4.py', '--engine', engine,
        '--scenario', scenario, '--detector-backend', 'yolo' if scenario == 'yolo' else 'color_fixture',
        '--output-dir', str(output), '--vision-camera-backend', args.vision_camera_backend,
        '--inference-rate-hz', str(args.inference_rate_hz)]
    if scenario == 'yolo':
        command += ['--weights-path', args.weights]
    if fault:
        command += ['--fault', fault]
    return command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir')
    parser.add_argument('--weights', default='')
    parser.add_argument('--image', default='')
    parser.add_argument('--mujoco-underlay', default='/home/jinho/ch13_mujoco_ws/install/setup.bash')
    parser.add_argument('--vision-camera-backend', choices=('upstream', 'snapshot'), default='upstream')
    parser.add_argument('--inference-rate-hz', type=float, default=10.)
    parser.add_argument('--audit-install-prefix')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    if args.audit_install_prefix:
        print(json.dumps(audit_installed_paths(args.audit_install_prefix, repo), indent=2))
        return 0
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
    packages = ['--packages-select', *PACKAGES]
    env = None

    def execute(key, command, kind='command', result_path=None, cwd=repo):
        value = run_command(key, command, output=output/key, batch_run_id=batch, cwd=cwd,
                            env=env, kind=kind, result_path=result_path,
                            camera_backend=args.vision_camera_backend)
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
        execute('installed_paths', [sys.executable, str(Path(__file__).resolve()),
                                   '--audit-install-prefix', str(install)])
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
                command = native_trial_command(args, engine, scenario, native, fault)
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
