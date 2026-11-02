"""Same-capture native command/velocity and original first carry failure."""
import hashlib,json,uuid
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/'native-g2-mujoco-242efeba-7b89-4d92-8b30-bbb3bb8f7e20'
closed=json.loads((root/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
owner=json.loads((root/'carry_failure_report.json').read_text());fault=owner['first_fault'];at=fault['ros_ns']
controller=json.loads((root/'controller_report.json').read_text())
trace=json.loads((root/'native_command_trace.json').read_text())
names=controller['command_publications']['joint_names'];native_names=trace['joints']
indices=[native_names.index(name) for name in names]
grip=[native_names.index(name) for name in ('gripper_left_joint','gripper_right_joint')]
packets=trace['pre_step']['rows'];changes=[];near=[]
for previous,current in zip(packets,packets[1:]):
    stamp=current['snapshot_ros_ns']
    if not at-500_000_000<=stamp<=at+20_000_000:continue
    delta=[current['ctrl'][i]-previous['ctrl'][i] for i in indices]
    if any(delta):
        changes.append(dict(capture_ns=stamp,step=max(abs(value) for value in delta),
            joint=names[max(range(len(delta)),key=lambda i:abs(delta[i]))],delta=delta))
    if abs(stamp-at)<=100_000_000:
        near.append(dict(capture_ns=stamp,gripper_velocity=[current['joint_velocity'][i] for i in grip],
            body_angular_velocity=current['body_angular_velocity']))
pubs=controller['command_publications']['rows'];publications=[]
for previous,current in zip(pubs,pubs[1:]):
    if not at-500_000_000<=current['decision_ros_ns']<=at+20_000_000:continue
    publications.append(dict(sequence=current['sequence'],ros_ns=current['decision_ros_ns'],
        decision_wall_ns=current['decision_wall_ns'],pub_wall_ns=current['publish_started_ns'],
        ros_interval_ns=current['decision_ros_ns']-previous['decision_ros_ns'],
        wall_interval_ns=current['decision_wall_ns']-previous['decision_wall_ns'],
        delta=[b-a for a,b in zip(previous['values'],current['values'])]))
frames=[];path=root/'observations.jsonl'
with path.open('rb') as source:
    source.seek(max(0,path.stat().st_size-12*1024*1024))
    for line in source:
        if not line.startswith(b'{"kind": "frame",'):continue
        row=json.loads(line)['value']
        if at-300_000_000<=row['ros_ns']<=at+20_000_000:
            frames.append(dict(ros_ns=row['ros_ns'],crawl=row['crawl'],
                contacts=row['samples']['contacts'],body=row['samples']['body']))
report=dict(scope='post_reap_original_same_capture_window_no_result_promotion',trial=root.name,
    first_fault={key:fault[key] for key in ('reason','ros_ns','wall_ns','selected_joint_sample')},
    original_report_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    reference_policy=controller['current']['reference_time_policy'],
    shift_clock=controller['current']['crawl_shift_reference_clock'],
    swing_clock=controller['current']['crawl_swing_reference_clock'],
    publications=publications,native_ctrl_changes=changes,native_gripper=near,frames=frames)
target=base/('gripper-window-'+str(uuid.uuid4()));target.mkdir()
(target/'window.json').write_text(json.dumps(report,indent=2));(target/'method.py').write_bytes(Path(__file__).read_bytes())
print(target,flush=True)
print(json.dumps(dict(first_fault={key:fault[key] for key in ('reason','ros_ns','wall_ns')},
    frames=[dict(ros_ns=row['ros_ns'],phase=row['crawl']['phase'],foot=row['crawl']['swing_foot']) for row in frames],
    pub_intervals_ms=[round(row['wall_interval_ns']/1e6,3) for row in publications],
    largest_changes=sorted(changes,key=lambda row:row['step'],reverse=True)[:3],
    shift_clock=report['shift_clock'],swing_clock=report['swing_clock'])),flush=True)
