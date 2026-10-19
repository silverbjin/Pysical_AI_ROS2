"""Post-run evidence evaluation. This never executes or claims new engine trials."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

repo = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo/'Ch13/scripts'))
from verify_all_13_4 import summarize
from verify_vision_13_4 import EvidenceRun, verdict
from run_vision_13_4 import required_checks

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
output = Path(args.output_dir).resolve()
output.mkdir(parents=True, exist_ok=False)
batch = str(uuid.uuid4())
results = {}


def proof(key, paths, accepted):
    directory = output/f'g{len(results):02d}'
    with EvidenceRun(directory, {'executed', 'verification'}) as run:
        run.result.update(group=key, batch_run_id=batch,
            role='Post-run integrity/criteria evaluation, NOT a new simulation',
            original_inputs=[str(path.relative_to(repo)) for path in paths])
        for i, source in enumerate(paths):
            if source.stat().st_size == 0:
                continue  # An empty probe log is not positive evidence; raw file remains intact.
            target = directory/f'input{i:02d}{source.suffix}'
            shutil.copyfile(source, target)
            run.artifact(target)
        try:
            run.finish(dict(executed=True, verification=bool(accepted)))
        except RuntimeError:
            pass
    results[key] = run.result


for key, filename, pattern in (
    ('build', 'auto-camera-build.log', r'Summary: 5 packages finished'),
    ('pytest', 'final-suite.log', r'\b[1-9][0-9]* passed'),
    ('colcon', 'final-colcon.log', r'Summary: 5 packages finished'),
    ('colcon_result', 'final-colcon-result.log', r'Summary: 123 tests, 0 errors, 0 failures, 0 skipped')):
    path = root/filename
    proof(key, [path], re.search(pattern, path.read_text()) is not None)
installed = root/'final-installed.json'
installed_value = json.loads(installed.read_text())
proof('installed_paths', [installed], len(installed_value) == 5 and
      installed_value['integrated_robot_camera']['license_verified'])

groups = {
    'geometry_mujoco': [('ms', 'static'), ('clean/md', 'delay')],
    'geometry_gazebo': [('gs', 'static'), ('gd', 'delay')],
    'yolo_mujoco': [('my', 'yolo')], 'yolo_gazebo': [('gy', 'yolo')],
    'tracking_mujoco': [(f'clean/m{rate}{repeat}', 'tracking')
                        for rate in (10, 15) for repeat in ('a', 'b', 'c')],
    'tracking_gazebo': [('gt', 'tracking')],
    **{f'safety_{fault}_{engine}': [(prefix+alias, 'safety')]
       for engine, prefix in (('mujoco', 'm'), ('gazebo', 'g'))
       for fault, alias in (('images', 'si'), ('tf', 'st'), ('joints', 'sj'))},
}
for key, trials in groups.items():
    paths, accepted = [], True
    engine = key.rsplit('_', 1)[-1]
    for name, scenario in trials:
        path = root/name/'result.json'
        value = json.loads(path.read_text())
        accepted = accepted and verdict(value, required_checks(scenario, engine=engine,
            camera_backend='snapshot' if engine == 'mujoco' else 'upstream')) == 'PASS'
        paths.append(path)
    proof(key, paths, accepted)
for engine, alias in (('mujoco', 'ml'), ('gazebo', 'gl')):
    path = root/alias/'result.json'
    value = json.loads(path.read_text())
    logs = sorted((root/alias).glob('*.log'))
    accepted = value.get('status') == 'PASS' and value.get('runtime_shutdown') == 'PASS'
    accepted = accepted and not any(marker in log.read_text() for log in logs for marker in (
        'Traceback', 'escalating to', 'process has died', 'failed to terminate'))
    proof('legacy_'+engine, [path, *logs], accepted)

summary = summarize(results, batch)
summary.update(role='Existing fail-closed summarizer over post-run evaluations; no new engines',
    measured_source_head='6828b82fd13c97dba3fc935325a741e583a830aa',
    audit_source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
    cohort_ids=['66d636a0-ef69-466b-b16f-7b95ca1bd6ac', '9e46415e-8589-4d4a-8032-cd31ac2d8599'])
assert summary['status'] == 'FAIL', 'This cohort must never become whole-section PASS'
(output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(dict(status=summary['status'], run_id=batch, output=str(output))))
