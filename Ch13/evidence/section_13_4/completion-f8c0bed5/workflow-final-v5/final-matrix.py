"""Frozen source/install matrix; stop at the first failed product trial."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
from verify_vision_13_4 import source_snapshot, file_digest
from verify_all_13_4 import audit_installed_paths
from run_vision_13_4 import required_checks

base = Path(os.environ['CH13_EGL_EVIDENCE'])
batch_name = os.environ.get('CH13_FINAL_NAME', 'final')
if Path(batch_name).name != batch_name or not batch_name.startswith('final'):
    raise ValueError('new final batch must be one directory inside this evidence root')
root = base / batch_name
prefix = Path(os.environ['CH13_EGL_INSTALL'])
mode = sys.argv[1]

def installation_files():
    return {str(path.relative_to(prefix)): file_digest(path)
            for path in sorted(prefix.rglob('*')) if path.is_file()
            and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')}

if mode == 'freeze':
    root.mkdir()
    snapshot = source_snapshot(Path.cwd())
    rows = audit_installed_paths(prefix, Path.cwd())
    baseline = Path('Ch13/evidence/section_13_4/egl-424240ff')
    for path in baseline.glob('*/result.json'):
        value = json.loads(path.read_text())
        engine, scenario = value.get('engine'), value.get('scenario')
        if engine in ('mujoco', 'gazebo') and scenario in ('static', 'delay', 'yolo', 'tracking', 'safety'):
            current = required_checks(scenario, engine=engine,
                camera_backend='snapshot' if engine == 'mujoco' else 'upstream')
            if not set(value['required_checks']) <= current:
                raise RuntimeError('required checks reduced relative to '+str(path))
    value = dict(batch_uuid=str(uuid.uuid4()), snapshot=snapshot, installed=installation_files(),
        installation_audit=rows, environment={key: os.environ.get(key) for key in
        ('LP_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LD_PRELOAD',
         'ROS_DOMAIN_ID', 'MUJOCO_GL')})
    (root/'frozen-source.json').write_text(json.dumps(value, indent=2)+'\n')
    for relative, digest in snapshot['files'].items():
        data = Path(relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError('source changed while archiving frozen batch: '+relative)
        destination = root/'source_archive'/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    print(json.dumps(dict(frozen=True, batch_uuid=value['batch_uuid'],
        source_files=len(snapshot['files']), installed_files=len(value['installed']))), flush=True)
    raise SystemExit(0)

frozen_path = root/'frozen-source.json'
frozen = json.loads(frozen_path.read_text())

def check_frozen():
    for relative, digest in frozen['snapshot']['files'].items():
        if file_digest(Path(relative)) != digest:
            raise RuntimeError('source changed after freeze: '+relative)
    if installation_files() != frozen['installed']:
        raise RuntimeError('installation changed after freeze')

check_frozen()
os.environ['CH13_EGL_EVIDENCE'] = str(root)
source = Path('Ch13/evidence/section_13_4/egl-424240ff/workflow/native-matrix.py').read_text()
scope = {'__name__': '__frozen_matrix__'}
exec(compile(source.split('group = sys.argv[1]')[0], 'native-matrix.py', 'exec'), scope)

def trial(label, engine, scenario, *extra):
    check_frozen()
    scope['trial'](label, engine, scenario, *extra)
    result = json.loads((root/label/'result.json').read_text())
    snapshot = json.loads((root/label/'source_snapshot.json').read_text())
    if snapshot['files'] != frozen['snapshot']['files']:
        raise RuntimeError('trial did not run frozen sources: '+label)
    check_frozen()
    record = dict(label=label, run_id=result['run_id'], status=result['status'],
        batch_uuid=frozen['batch_uuid'], frozen_manifest_sha256=file_digest(frozen_path))
    with (root/'frozen-progress.jsonl').open('a') as stream:
        stream.write(json.dumps(record)+'\n')
    if result['status'] != 'PASS':
        raise RuntimeError('product failure preserved; stop batch at '+label)

if mode == 'geometry':
    trial('static-off', 'mujoco', 'static')
    trial('static-on', 'mujoco', 'static', '--trace-enabled')
    trial('delay-on', 'mujoco', 'delay', '--trace-enabled', '--processing-delay-s', '.15')
elif mode == 'tracking':
    for rate in (10, 15):
        for suffix in 'abc':
            trial(f'm{rate}{suffix}', 'mujoco', 'tracking', '--trace-enabled',
                  '--inference-rate-hz', str(rate))
elif mode == 'remaining':
    for engine in ('mujoco', 'gazebo'):
        trial(engine+'-cup', engine, 'yolo', '--trace-enabled')
        for fault in ('images', 'tf', 'joints'):
            trial(engine+'-'+fault, engine, 'safety', '--fault', fault, '--trace-enabled')
    for scenario in ('static', 'delay'):
        trial('gazebo-'+scenario, 'gazebo', scenario, '--trace-enabled',
              *(['--processing-delay-s', '.15'] if scenario == 'delay' else []))
    # Original matrix has one Gazebo tracking trial; two additional runs give
    # three consecutive results under the same frozen sources and installation.
    for suffix in 'abc':
        trial('gazebo-tracking-'+suffix, 'gazebo', 'tracking', '--trace-enabled')
elif mode == 'legacy':
    exec(compile(Path('Ch13/evidence/section_13_4/egl-424240ff/workflow/legacy.py').read_text(),
                 'legacy.py', 'exec'), {'__name__': '__frozen_legacy__'})
    check_frozen()
else:
    raise ValueError(mode)
