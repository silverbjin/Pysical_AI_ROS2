"""Supplementary offline check: was an arm goal change recorded during SHIFT?"""
import hashlib
import json
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
root = here.parent/'native-g1-mujoco-61422188-2d9d-4915-bdaf-eb06a8b1e4e0'
analysis = json.loads((here/'result.json').read_text())
times = {row['snapshot_capture_ns'] for row in analysis['reference_rows']}
source = root/'native_controls.json'
rows = [r for r in json.loads(source.read_text())['records'] if r['capture_ns'] in times]
names = ['arm_joint_'+str(i) for i in range(1, 7)]+['gripper_left_joint', 'gripper_right_joint']
summary = {}
for name in names:
    values = [next(a for a in r['actuators'] if a['joint_name'] == name) for r in rows]
    controls = [v['ctrl'] for v in values]
    summary[name] = dict(staged_ctrl_min=min(controls), staged_ctrl_max=max(controls),
        distinct_staged_ctrl_count=len(set(controls)),
        max_abs_snapshot_velocity=max(abs(v['velocity']) for v in values),
        kp=values[0]['kp'], kv=values[0]['kv'])
assert all(v['distinct_staged_ctrl_count'] == 1 for v in summary.values())
out = dict(scope='offline_staged_arm_goal_check_not_physical_acceptance_or_causality',
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    reference_analysis_sha256=hashlib.sha256((here/'result.json').read_bytes()).hexdigest(),
    native_controls_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    sample_count=len(rows), joints=summary,
    conclusion='No arm/gripper staged goal change in selected SHIFT snapshots; inter-sample changes and motor application times not traced')
with Path(sys.argv[1]).open('x') as file:
    json.dump(out, file, indent=2, allow_nan=False)
    file.write('\n')
print(json.dumps(out, separators=(',', ':')))
