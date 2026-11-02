"""Finite, sequential Gazebo command-semantics experiment, never robot acceptance."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

source = Path(__file__).resolve().parent
root = Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b')
run_id = str(uuid.uuid4())
out = root / 'evidence' / ('force-semantics-' + run_id)
out.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {'scope': 'single_joint_force_semantics_not_C1_G2_acceptance', 'uuid': run_id,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'inputs': {p.name: sha(p) for p in source.iterdir() if p.is_file()},
            'conditions_predefined': ['every_step', 'control_period'],
            'dt_s': .002, 'inertia_kg_m2': .1, 'torque_nm': 1., 'drive_steps': 100,
            'environment_changes': 'unique GZ_PARTITION only; no service/clock/driver changes',
            'commands': [], 'results': []}
def invoke(command, label, env=None):
    manifest['commands'].append({'label': label, 'argv': command})
    with (out/(label+'.stdout')).open('w') as stdout, (out/(label+'.stderr')).open('w') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr, env=env, check=False)
    manifest['results'].append({'label': label, 'returncode': result.returncode})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    return result.returncode
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gz-sim8'], text=True))
binary = out/'force_probe'
rc = invoke(['g++', '-O2', '-std=c++17', str(source/'force_probe.cpp'), '-o', str(binary), *flags], 'build')
if rc:
    print((out/'build.stderr').read_text()[-5000:]); print(out); sys.exit(rc)
manifest['binary_sha256'] = sha(binary)
manifest['packages'] = subprocess.check_output(['dpkg-query', '-W', 'ros-jazzy-gz-sim-vendor',
    'ros-jazzy-gz-physics-vendor', 'ros-jazzy-gz-ros2-control', 'ros-jazzy-hardware-interface'], text=True)
env = dict(os.environ, GZ_PARTITION='ch13-force-'+run_id)
overall = 0
for mode in manifest['conditions_predefined']:
    rc = invoke([str(binary), str(source/'force_probe.sdf'), mode], mode, env)
    print((out/(mode+'.stderr')).read_text()[-1800:])
    if rc:
        overall=rc
        break
processes = subprocess.check_output(['ps', '-eo', 'pid,args'], text=True)
manifest['residual_process_lines'] = [line for line in processes.splitlines() if str(binary) in line]
manifest['all_conditions_pass'] = len(manifest['results'])==3 and all(x['returncode']==0 for x in manifest['results'])
for mode in manifest['conditions_predefined']:
    p=out/(mode+'.stdout')
    if p.exists():
        with p.open() as f:
            rows=list(csv.DictReader(f))
        if len(rows)==110:
            manifest.setdefault('summary', {})[mode] = {'delta_qd': float(rows[-1]['velocity_rad_s'])-float(rows[9]['velocity_rad_s']),
                'first_drive_rows': rows[10:17], 'last': rows[-1]}
manifest['output_sha256']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'path':str(out),'all_conditions_pass':manifest['all_conditions_pass'],
                 'residual':manifest['residual_process_lines']}, indent=2))
sys.exit(overall or bool(manifest['residual_process_lines']))
