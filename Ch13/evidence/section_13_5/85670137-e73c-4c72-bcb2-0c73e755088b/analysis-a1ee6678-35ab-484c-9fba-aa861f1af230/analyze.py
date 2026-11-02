"""Read-only postmortem of 61422188; NOT an engine or acceptance test.

Run from the repository with /usr/bin/python3 (numpy required):
  python3 Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/analysis-a1ee6678-35ab-484c-9fba-aa861f1af230/analyze.py OUTPUT.json
The output must not exist. No ROS, simulator, actuator or root-state APIs are used.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

here = Path(__file__).resolve().parent
repo = next(p for p in here.parents if (p/'Ch13/ros2_ws/src').is_dir())
for package in ('integrated_robot_navigation', 'integrated_robot_vision'):
    sys.path.insert(0, str(repo/'Ch13/ros2_ws/src'/package))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import fk_leg

root = here.parent/'native-g1-mujoco-61422188-2d9d-4915-bdaf-eb06a8b1e4e0'
scene = root.with_name(root.name+'-prepared')/'scene'
inputs = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    inputs[str(path.relative_to(repo))] = digest(path)
    return json.loads(path.read_text())


def blend(u):
    return u*u*u*(10.+u*(-15.+6.*u))


def inverse_blend(weight):
    assert -1e-12 <= weight <= 1.+1e-12
    lo, hi = 0., 1.
    for _ in range(64):
        mid = (lo+hi)/2
        if blend(mid) < weight:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


# Pure mathematical checks, not robot/simulation success.
for u in (.01, .1, .4, .8, .99):
    assert abs(inverse_blend(blend(u))-u) < 1e-10

report = load(root/'controller_report.json')
manifest = load(root/'source_manifest.json')
changed = [rel for rel, sha in manifest['files'].items()
           if not (repo/rel).is_file() or digest(repo/rel) != sha]
assert not changed, changed
raw = (scene/'robot.urdf').read_text()
inputs[str((scene/'robot.urdf').relative_to(repo))] = digest(scene/'robot.urdf')
model = compile_model(raw)
assert model.model_sha256 == report['model_sha256']
native = load(root/'native_controls.json')['records']
carry = load(root/'carry_failure_report.json')['first_fault']
result = load(root/'result.json')
teardown = load(root/'teardown.json')
cur = report['current']
assert cur['phase'] == 'SHIFT' and cur['swing_foot'] is None
assert cur['unload_start_ns'] is None and cur['calibration']['vertical'] is None
R = np.asarray(cur['reference_body'])[:3, :3]
assert np.allclose(R.T@R, np.eye(3), atol=1e-12, rtol=0.)
fixed_feet = ('fr_foot', 'rr_foot', 'rl_foot')  # G1 ORDER[0] is fl_foot.
phase_start = cur['phase_start_ns']
selected = [r for r in native if phase_start <= r['capture_ns'] <= 32100000000]
rows, parity = [], []
for record in selected:
    actuators = {a['joint_name']: a for a in record['actuators']}
    translations = {}
    for foot in fixed_feet:
        names = [foot[:2]+'_'+part+'_joint' for part in ('hip', 'thigh', 'calf')]
        angles = [actuators[name]['ctrl'] for name in names]
        fast = np.array(fk_leg(model, foot, angles))
        # Independent general URDF matrix chain checks the optimized analytic FK.
        q = dict(zip(names, angles))
        general = np.linalg.solve(model.chains['base_link'].forward(q),
                                  model.chains[foot].forward(q))[:3, 3]
        parity.append(float(np.linalg.norm(fast-general)))
        translations[foot] = np.array(cur['targets'][foot])-R@fast
    values = np.array(list(translations.values()))
    center = values.mean(axis=0)
    rows.append(dict(snapshot_capture_ns=record['capture_ns'],
        probe_received_ns=record['received_ns'],
        implied_command_translation_m=center.tolist(),
        fixed_leg_translation_spread_m=max(float(np.linalg.norm(v-center)) for v in values),
        per_leg_translation_m={f:v.tolist() for f,v in translations.items()},
        fr_thigh_staged_ctrl_rad=actuators['fr_thigh_joint']['ctrl'],
        snapshot_arm_joint_2_velocity_rps=actuators['arm_joint_2']['velocity']))
assert max(parity) < 1e-12
assert max(r['fixed_leg_translation_spread_m'] for r in rows) < 1e-12
# Check sensitivity of the coherence criterion; no synthetic data are merged with observations.
changed_q = {a['joint_name']: a['ctrl'] for a in selected[-1]['actuators']}
nominal_q = [changed_q['fr_'+part+'_joint'] for part in ('hip', 'thigh', 'calf')]
perturbed_q = nominal_q.copy()
perturbed_q[1] += .001
negative_displacement = float(np.linalg.norm(np.array(fk_leg(model, 'fr_foot', perturbed_q))
                                            -np.array(fk_leg(model, 'fr_foot', nominal_q))))
assert negative_displacement > 1e-5

# Conditional reconstruction: commanded reference ONLY, never measured root pose/odometry.
# G1 zero command -> constant travel and rotation; only FL preconditioning changes a foot.
# _plan_shift: duration=sqrt((10sqrt(3)/3)*distance/accel); G1 _body_duration returns minimum.
duration = cur['shift_duration_s']
accel = cur['calibration']['shift_accel_budget_mps2']
distance = duration**2*accel/(10*math.sqrt(3)/3)
start = np.array(rows[0]['implied_command_translation_m'])
direction = np.array(rows[-1]['implied_command_translation_m'])-start
delta = direction/np.linalg.norm(direction)*distance
for row in rows:
    position = np.array(row['implied_command_translation_m'])
    weight = float((position-start)@delta/(distance**2))
    residual = float(np.linalg.norm(position-start-weight*delta))
    assert residual < 1e-12
    row['curve_line_residual_m'] = residual
    row['curve_implied_decision_ns_not_direct_trace'] = round(
        phase_start+inverse_blend(weight)*duration*1e9)
    row['curve_implied_lag_vs_snapshot_ms_not_apply_latency'] = (
        row['snapshot_capture_ns']-row['curve_implied_decision_ns_not_direct_trace'])/1e6

clock_path = root/'control_clock.jsonl'
inputs[str(clock_path.relative_to(repo))] = digest(clock_path)
clock_rows = [json.loads(line) for line in clock_path.read_text().splitlines()]
clock_window = [r for r in clock_rows if r.get('event') == 'publish'
                and carry['wall_ns']-200_000_000 <= r.get('published_wall_ns', -1) <= carry['wall_ns']]
observations_path = root/'observations.jsonl'
inputs[str(observations_path.relative_to(repo))] = digest(observations_path)
kinds = collections.Counter()
joint_window = []
with observations_path.open() as file:
    for line in file:
        row = json.loads(line)
        kinds[row['kind']] += 1
        v = row['value']
        if row['kind'] == 'joints' and abs(v['stamp_ns']-carry['ros_ns']) <= 80_000_000:
            joint_window.append(dict(header_ns=v['stamp_ns'], first_received_ns=v['received_ns'],
                arm_joint_2_velocity_rps=v['data']['velocity']['arm_joint_2']))
assert any(r['arm_joint_2_velocity_rps'] == carry['selected_joint_sample']['data']['velocity']['arm_joint_2']
           for r in joint_window)

external = Path('/home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control')
external_head = subprocess.check_output(['git', '-C', str(external), 'rev-parse', 'HEAD'], text=True).strip()
external_status = subprocess.check_output(['git', '-C', str(external), 'status', '--porcelain'], text=True)
source_ranges = {
    'mujoco_ros2_control/src/mujoco_system_interface.cpp': [(1005, 1018), (1172, 1184), (1209, 1220)],
    'mujoco_ros2_control/src/mujoco_simulation.cpp': [(1364, 1370), (1407, 1419), (1518, 1526)],
    'mujoco_ros2_control/src/mujoco_ros2_control_node.cpp': [(152, 175)],
    'mujoco_ros2_control_plugins/include/mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp': [(30, 38)]}
external_sources = {}
for rel, ranges in source_ranges.items():
    path = external/rel
    lines = path.read_text().splitlines()
    external_sources[rel] = dict(sha256=digest(path), excerpts=[dict(first_line=lo,
        last_line=hi, text='\n'.join(lines[lo-1:hi])) for lo, hi in ranges])
archive = here.parent/'task8-g1-latest-guard-mujoco-61422188.zip'
archive_sha = digest(archive)
assert archive_sha == '42d461db29e4b87af0b99ccbfb090bdd74f1c6c1d3a3a034243dd2017065b21e'
out = dict(schema=1, analysis_id=here.name, scope='offline_analysis_only_not_new_engine_or_acceptance',
    trial=root.name, analysis_source_sha256=digest(Path(__file__)), inputs=inputs,
    runtime_manifest_file_count=len(manifest['files']), runtime_mismatches=changed,
    model_sha256=model.model_sha256, original_archive_sha256=archive_sha,
    external_source=dict(repository='https://github.com/ros-controls/mujoco_ros2_control',
        head=external_head, status_porcelain=external_status, provenance_scope='postmortem_local_source_not_trial_binary_rebuild',
        license_sha256=digest(external/'LICENSE'), files=external_sources),
    original_status=result['status'],
    original_false_or_missing_required_checks=[k for k in result['required_checks'] if not result['checks'].get(k)],
    carry_fault=dict(reason=carry['reason'], header_ns=carry['ros_ns'], wall_ns=carry['wall_ns'],
        selected_header_ns=carry['selected_joint_sample']['stamp_ns'],
        selected_receipt_age_ms=(carry['wall_ns']-carry['selected_joint_sample']['received_ns'])/1e6,
        arm_joint_2_velocity_rps=carry['selected_joint_sample']['data']['velocity']['arm_joint_2']),
    joint_window=joint_window, observation_counts=dict(kinds),
    command_coherence=dict(count=len(rows), max_spread_m=max(r['fixed_leg_translation_spread_m'] for r in rows),
        analytic_vs_general_fk_max_error_m=max(parity), negative_control_displacement_m=negative_displacement),
    conditional_curve_reconstruction=dict(phase_start_ns=phase_start, duration_s=duration,
        distance_m=distance, start_translation_m=start.tolist(), delta_m=delta.tolist(),
        assumptions=['zero navigation command throughout G1', 'constant commanded rotation',
            'FR/RR/RL world reference targets fixed until stop', 'first selected reference is phase start',
            'G1 duration determined by quintic acceleration formula, no additional duration scaling'],
        limitation='Inverse curve timing is conditional, not a publish/callback/CM/physics application trace'),
    reference_rows=rows, clock_publish_window=clock_window,
    tick_spans_end_clock_not_decision_clock=report['first_stop']['tick_spans'],
    cleanup=dict(normal_runtime_exit=result['checks']['normal_runtime_exit'],
        normal_engine_exit=result['checks']['normal_engine_exit'],
        parent_reaped=result['checks']['parent_reaped'], no_residual_members=result['checks']['no_residual_members']),
    conclusions=dict(observed_vectors_coherent=True,
        staged_ctrl_with_older_physics_snapshot=True,
        mixed_joint_write_demonstrated=False,
        applied_command_timing_measured=False,
        leg_command_to_arm_peak_causality_proven=False,
        section_completed=False))
destination = Path(sys.argv[1])
with destination.open('x') as file:
    json.dump(out, file, ensure_ascii=False, indent=2, allow_nan=False)
    file.write('\n')
print(json.dumps(dict(output=str(destination), sha256=digest(destination),
    rows=len(rows), max_spread_m=out['command_coherence']['max_spread_m'],
    fk_parity_m=max(parity), runtime_files_unchanged=len(manifest['files']),
    carry_velocity=out['carry_fault']['arm_joint_2_velocity_rps'],
    original_failed_checks=out['original_false_or_missing_required_checks']), ensure_ascii=False))
