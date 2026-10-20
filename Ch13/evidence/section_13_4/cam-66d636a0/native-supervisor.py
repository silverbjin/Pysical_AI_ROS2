"""One-off serial diagnostic supervisor; not a product runner or acceptance shortcut."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo = Path.cwd().resolve()
sys.path.insert(0, str(repo/'Ch13/scripts'))
from verify_all_13_4 import run_command, residual_pids
from verify_vision_13_4 import verdict, source_snapshot
from run_vision_13_4 import required_checks, is_gazebo_command

root = repo/'Ch13/evidence/section_13_4/cam-66d636a0'
batch = '66d636a0-ef69-466b-b16f-7b95ca1bd6ac'
clean_cohort = '--clean' in sys.argv
if clean_cohort:
    root = root/'clean'
    batch = '9e46415e-8589-4d4a-8032-cd31ac2d8599'
root.mkdir(parents=True, exist_ok=True)
assert not (root/'matrix.json').exists(), 'Never overwrite or resume a native trial'


def inventory():
    found = []
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv = path.read_bytes()
            fields = (path.parent/'stat').read_text().rsplit(')', 1)[1].split()
            if fields[0] == 'Z':
                continue
            first = argv.split(b'\0', 1)[0]
            if (first.endswith(b'/mujoco_ros2_control/ros2_control_node')
                    or is_gazebo_command(argv)):
                found.append(dict(pid=int(path.parent.name), command=argv.decode(errors='replace')))
        except (OSError, ValueError, IndexError):
            pass
    return found


cases = [('ms', 'mujoco', 'static', 'snapshot', 10., None),
         ('md', 'mujoco', 'delay', 'snapshot', 10., None),
         ('my', 'mujoco', 'yolo', 'snapshot', 10., None)]
for rate in (10, 15):
    for repeat in ('a', 'b', 'c'):
        cases.append((f'm{rate}{repeat}', 'mujoco', 'tracking', 'snapshot', rate, None))
for rate in (10, 15):
    cases.append((f'mu{rate}', 'mujoco', 'tracking', 'upstream', rate, None))
for engine, prefix, backend in (('mujoco', 'm', 'snapshot'), ('gazebo', 'g', 'upstream')):
    if engine == 'gazebo':
        cases += [(prefix+alias, engine, scenario, backend, 10., None)
                  for alias, scenario in (('s', 'static'), ('d', 'delay'),
                                          ('y', 'yolo'), ('t', 'tracking'))]
    for alias, fault in (('si', 'images'), ('st', 'tf'), ('sj', 'joints')):
        cases.append((prefix+alias, engine, 'safety', backend, 10., fault))
    cases.append((prefix+'l', engine, 'legacy', 'upstream', 10., None))

if clean_cohort:
    cases = [('md', 'mujoco', 'delay', 'snapshot', 10., None)] + [
        (f'm{rate}{repeat}', 'mujoco', 'tracking', 'snapshot', rate, None)
        for rate in (10, 15) for repeat in ('a', 'b', 'c')]

matrix = dict(batch_run_id=batch, source_head=subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], text=True).strip(), status='RUNNING',
    scope='Native trials only; not whole section PASS',
    conditions={key: os.environ.get(key) for key in (
        'ROS_DOMAIN_ID', 'MUJOCO_GL', 'LP_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
    cases={alias: dict(engine=engine, scenario=scenario, backend=backend, rate_hz=rate,
                       fault=fault, status='UNVERIFIED')
           for alias, engine, scenario, backend, rate, fault in cases})


def save():
    (root/'matrix.json').write_text(json.dumps(matrix, indent=2)+'\n')


save()
try:
    assert not inventory(), 'Existing native engine: stop without signaling it'
    (root/'source.json').write_text(json.dumps(source_snapshot(repo), indent=2)+'\n')
    for alias, engine, scenario, backend, rate, fault in cases:
        assert not inventory(), 'Native engine remains; do not start next trial'
        output = root/alias
        if scenario == 'legacy':
            command = [sys.executable, 'Ch13/scripts/run_architecture_13_3.py',
                       '--engine', engine, '--output-dir', str(output)]
        else:
            command = [sys.executable, 'Ch13/scripts/run_vision_13_4.py',
                       '--engine', engine, '--scenario', scenario,
                       '--detector-backend', 'yolo' if scenario == 'yolo' else 'color_fixture',
                       '--vision-camera-backend', backend, '--inference-rate-hz', str(rate),
                       '--output-dir', str(output)]
            if scenario == 'yolo':
                command += ['--weights-path', '/home/jinho/ch13_vision_13_4_assets/yolov8n.pt']
            if fault:
                command += ['--fault', fault]
        wrapper = run_command(alias, command, output=root/(alias+'w'),
                              batch_run_id=batch, cwd=repo)
        value = json.loads((output/'result.json').read_text())
        if scenario == 'legacy':
            fresh = (output/'result.json').stat().st_mtime >= wrapper['started_at']
            cleanup = not inventory()
            logs_clean = not any(marker in logfile.read_text() for logfile in output.glob('*.log')
                for marker in ('Traceback', 'escalating to', 'process has died', 'failed to terminate'))
            accepted = (value.get('status') == 'PASS' and value.get('runtime_shutdown') == 'PASS'
                        and wrapper['returncode'] == 0 and logs_clean)
        else:
            fresh = value['started_at'] >= wrapper['started_at']
            cleanup = not residual_pids(output/'result.json')
            accepted = verdict(value, required_checks(scenario, engine=engine,
                                                       camera_backend=backend)) == 'PASS'
        row = matrix['cases'][alias]
        row.update(status='PASS' if fresh and cleanup and accepted else 'FAIL',
                   returncode=wrapper.get('returncode'), run_id=value.get('run_id'),
                   cleanup=value.get('cleanup'), errors=value.get('errors'),
                   checks=value.get('checks'), geometry=value.get('geometry'),
                   recognition=value.get('recognition'), tracking_metrics=value.get('tracking_metrics'),
                   runtime_shutdown=value.get('runtime_shutdown'), remaining_native_processes=inventory())
        save()
        print(alias+': '+row['status'], flush=True)
        assert cleanup and not row['remaining_native_processes'], 'Cleanup unconfirmed'
    matrix['status'] = 'PASS' if all(row['status'] == 'PASS' for row in matrix['cases'].values()) else 'FAIL'
except BaseException as error:
    matrix.update(status='STOPPED', supervisor_error=repr(error))
    raise
finally:
    matrix.update(remaining_native_processes=inventory(), finished_at=time.time())
    save()
