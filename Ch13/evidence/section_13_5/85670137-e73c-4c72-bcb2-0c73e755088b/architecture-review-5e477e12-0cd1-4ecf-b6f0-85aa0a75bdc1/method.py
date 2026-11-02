"""Read-only architecture review of eight closed trials; no engine attempts."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,subprocess,uuid
import integrated_robot_navigation.gait as gait
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.model import compile_model

repo=Path.cwd().resolve();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
ids=['1a27f18c-e6c7-4d36-b7f4-99a245f79d0f','afa0c4d9-0a46-4393-a123-4b1dbc2a4545',
 'b9c835b2-0b3d-4365-a56e-3dc7a9a65ce7','c6ee257f-512c-487b-9a1f-1f2be2ac05e1',
 '4342c86d-3d22-4577-82bb-6880490c8fb8','15382b7e-0d5f-45dd-95f3-6500573a3f60',
 'b82af967-a8a8-4e11-9612-6db8cb5d6695','b8360ed1-0caf-4a98-91bb-c80eda79f1ac']
latest=base/('native-g2-gazebo-'+ids[-1]);cases=[];inputs={}
for key in ids:
    trial=base/('native-g2-gazebo-'+key)
    values={}
    for name in ('result.json','controller_report.json','teardown.json'):
        p=trial/name;raw=p.read_bytes();inputs[str(p.relative_to(repo))]=hashlib.sha256(raw).hexdigest()
        values[name]=json.loads(raw)
    r,c,t=(values[n] for n in ('result.json','controller_report.json','teardown.json'))
    assert t['parent_reaped'] and not t['forced_cleanup'] and t['residual_live_pids']==[]
    fault=c['first_fault'];kind='force_transfer'
    if fault is None:
        p=trial/'carry_failure_report.json';raw=p.read_bytes();fault=json.loads(raw)['first_fault']
        inputs[str(p.relative_to(repo))]=hashlib.sha256(raw).hexdigest();kind='carry'
    elif fault['reason']=='thigh/trunk collision clearance':kind='reference_geometry'
    contacts=fault.get('samples',{}).get('contacts',{}).get('data',{})
    selected=fault.get('state_before',{}).get('swing_foot') if isinstance(fault.get('state_before'),dict) else None
    force=contacts['forces'][contacts['names'].index(selected)] if selected else None
    cases.append(dict(trial=trial.name,status=r['status'],category=kind,reason=fault['reason'],
        ros_ns=fault['ros_ns'],selected=selected,selected_force_n=force,
        measured_stop=t['runtime_shutdown']['steps']['measured_stop'],
        engine_process_exit_codes=t['engine_returncodes'],actual_carry_terminal=r['checks']['carry_terminal_received'],
        parent_reaped=t['parent_reaped'],forced_cleanup=t['forced_cleanup'],residual=t['residual_live_pids']))

source=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/gait.py'
assert source.read_bytes()==Path(gait.__file__).read_bytes(),'installed gait/source mismatch'
run=json.loads((latest/'result.json').read_text());report=json.loads((latest/'controller_report.json').read_text())
limits=default_limits();model=compile_model(Path(run['scene']['robot']['path']).read_text())
m=gait.CrawlMachine(model,limits);m.state='CRAWL';m.phase='SHIFT';m.swing_foot='fr_foot';m._unload_start=1
m._fail('measured unload timeout')
first=dict(state=m.state,primary_reason=m.reason,landing_foot=m._fault_landing_foot)
m._fail('fault landing measured support/settle lost')
second=dict(state=m.state,primary_reason=m.reason,landing_foot=m._fault_landing_foot)
body=report['first_fault']['samples']['body']['data']
speed=math.sqrt(sum(v*v for v in body['linear_velocity']))
angular=math.sqrt(sum(v*v for v in body['angular_velocity']))
budget=gait.CrawlMachine.TRAVEL_BUDGET['SHIFT'];shift_min=m._body_duration('SHIFT',.7)
# _body_duration uses the normal CRAWL state. The fault component above is
# latched FAULT, so use a separate unactivated normal-mode arithmetic object.
normal=gait.CrawlMachine(model,limits);normal.state='CRAWL'
shift_min=normal._body_duration('SHIFT',.7)
progress=budget*limits['max_vx'];peak_required=.6/240.
minimum_bump_times={f:(16/(3*math.sqrt(3)))*max(0.,report['current']['floor'][f]
    +limits['swing_height_m']-report['current']['stance_reference_z'][f]-limits['max_unload_height_m'])
    /limits['max_swing_speed_mps'] for f in model.feet}
out=base/('architecture-review-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
sources={}
for relative in ('Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/gait.py',
 'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/contact_transfer.py',
 'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/reference_envelope.py',
 'Ch13/ros2_ws/src/integrated_robot_navigation_sensors/src/gazebo_position_system.cpp',
 'Ch13/scripts/run_navigation_13_5.py','Ch13/docs/SECTION_13_5_IMPLEMENTATION_PLAN_KO.md'):
    sources[relative]=hashlib.sha256((repo/relative).read_bytes()).hexdigest()
value=dict(scope=__doc__,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    engine_attempts=0,source_changes=0,source_sha256=sources,input_sha256=inputs,cases=cases,
    counts=dict(Counter(c['category'] for c in cases)),
    recovery_counterexample=dict(scope='executed_kernel_error_transitions_not_proof_of_actual_second_fault',
        first=first,second=second,latest_fault_measured_speed_mps=speed,
        latest_fault_measured_angular_rps=angular,stop_limits=[limits['stopped_v_mps'],limits['stopped_wz_rps']],
        actual_secondary_reason_not_recorded=True),
    reference_timing=dict(scope='commanded_travel_arithmetic_not_native_arrival_proof',
        shift_travel_m=progress,minimum_shift_s=shift_min,
        shift_only_mean_mps=progress/shift_min,required_mean_mps=peak_required,
        shift_only_time_for_0_6m_s=.6/progress*shift_min,
        minimum_swing_bump_time_s=minimum_bump_times,
        optimistic_travel_mean_with_minimum_bump_mps=progress/(shift_min+min(minimum_bump_times.values())),
        excluded=['unload','touchdown','settle','planning','body support offset','physical tracking/engine rate']))
(out/'result.json').write_text(json.dumps(value,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),counts=value['counts'],recovery=value['recovery_counterexample'],
    timing=value['reference_timing'])),flush=True)
