"""Approved sequential trials; product FAIL never becomes workflow PASS."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(os.environ['CH13_EGL_EVIDENCE'])

def live_engines():
    found = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            argv = (p/'cmdline').read_bytes().decode(errors='replace').split('\0')
            stat = (p/'stat').read_text().split(') ', 1)[1].split()
            native = (Path(argv[0]).name in {'ros2_control_node', 'gz', 'gzserver'}
                      or (any(Path(a).name == 'gz' for a in argv) and 'sim' in argv)
                      or any('/gz/sim' in a or 'gz-sim-server' in a for a in argv))
            if native and stat[0] != 'Z':
                found.append({'pid': int(p.name), 'argv': argv})
        except (OSError, IndexError):
            pass
    return found

def trial(label, engine, scenario, *extra):
    before = live_engines()
    if before:
        raise RuntimeError('Unowned/existing engine present; no signals sent: '+repr(before))
    output = root/label
    if output.exists():
        raise FileExistsError(output)
    command = [sys.executable, 'Ch13/scripts/run_vision_13_4.py', '--engine', engine,
               '--scenario', scenario, '--output-dir', str(output)]
    if scenario == 'yolo':
        command += ['--detector-backend', 'yolo', '--weights-path',
                    '/home/jinho/ch13_vision_13_4_assets/yolov8n.pt']
    else:
        command += ['--detector-backend', 'color_fixture']
    if engine == 'mujoco':
        command += ['--vision-camera-backend', 'snapshot']
    command += list(extra)
    print('START '+label, flush=True)
    started = time.time()
    with (root/(label+'-runner.log')).open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    data = json.loads((output/'result.json').read_text())
    cleanup = data.get('cleanup')
    after = live_engines()
    safe = (bool(cleanup) and all(v.get('residual_live_pids') == [] for v in cleanup)
            and not after)
    record = dict(label=label, run_id=data.get('run_id'), command=command,
                  returncode=result.returncode, status=data['status'],
                  failed_checks=[k for k,v in data.get('checks',{}).items() if not v],
                  cleanup_confirmed=safe, live_engines_after=after,
                  started_at=started, finished_at=time.time())
    with (root/'matrix-progress.jsonl').open('a') as log:
        log.write(json.dumps(record)+'\n')
    print(json.dumps(record), flush=True)
    if not safe:
        raise RuntimeError('Cleanup unconfirmed: stop matrix without starting another engine')

group = sys.argv[1]
if group == 'geometry':
    trial('static-off', 'mujoco', 'static')
    trial('static-on', 'mujoco', 'static', '--trace-enabled')
    trial('delay-on', 'mujoco', 'delay', '--trace-enabled', '--processing-delay-s', '.15')
elif group == 'tracking':
    for rate in (10, 15):
        for suffix in 'abc':
            trial(f'm{rate}{suffix}', 'mujoco', 'tracking', '--trace-enabled',
                  '--inference-rate-hz', str(rate))
elif group == 'remaining':
    for engine in ('mujoco', 'gazebo'):
        trial(engine+'-cup', engine, 'yolo', '--trace-enabled')
        for fault in ('images', 'tf', 'joints'):
            trial(engine+'-'+fault, engine, 'safety', '--fault', fault, '--trace-enabled')
    for scenario in ('static', 'delay', 'tracking'):
        trial('gazebo-'+scenario, 'gazebo', scenario, '--trace-enabled',
              *(['--processing-delay-s', '.15'] if scenario == 'delay' else []))
else:
    raise ValueError(group)
