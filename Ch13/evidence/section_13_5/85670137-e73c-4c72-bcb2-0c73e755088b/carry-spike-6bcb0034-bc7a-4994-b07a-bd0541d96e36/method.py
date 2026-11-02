"""Stream the completed original, retaining every exceedance and two small windows."""
import hashlib,json,uuid
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial='native-g2-mujoco-095dc500-a35b-48c5-b81c-cef60e90f964'
root=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/trial
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids'] and closed['finalization_complete']
result=json.loads((root/'result.json').read_text())
assert result['status']=='FAIL' and [k for k,v in result['checks'].items() if not v]==['carry_measured_settle']
out=base/('carry-spike-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
operational={'stand','calibrate','forward','left','right','reverse','stopped'}
grip=('gripper_left_joint','gripper_right_joint')
bad=[];maximum=None;frames=0;identities=set();source_sha=hashlib.sha256()
with (root/'observations.jsonl').open('rb') as source:
    for line in source:
        source_sha.update(line)
        if not line.startswith(b'{"kind": "frame",'):continue
        row=json.loads(line)['value']
        if row['stage'] not in operational:continue
        frames+=1;sample=row['samples']['joints'];identities.add(sample['stamp_ns'])
        speeds={name:sample['data']['velocity'][name] for name in grip}
        speed=max(map(abs,speeds.values()))
        summary=dict(frame_ros_ns=row['ros_ns'],frame_wall_ns=row['wall_ns'],stage=row['stage'],
            joint_stamp_ns=sample['stamp_ns'],joint_received_ns=sample['received_ns'],speed=speed,
            gripper_velocity=speeds,crawl=row['crawl'],joints=sample,
            body=row['samples']['body'],contacts=row['samples']['contacts'])
        if maximum is None or speed>maximum['speed']:maximum=summary
        if speed>.005:bad.append(summary)
assert maximum and bad
targets=sorted({bad[0]['joint_stamp_ns'],maximum['joint_stamp_ns']})
def near(stamp):return any(abs(stamp-at)<=600_000_000 for at in targets)
counts={};window=out/'window.jsonl'
with window.open('x') as output,(root/'observations.jsonl').open('rb') as source:
    for line in source:
        kind=None
        for key in ('frame','native_controls','joints','movement_decision','carry_state'):
            if line.startswith(('{"kind": "'+key+'",').encode()):kind=key;break
        if kind is None:continue
        row=json.loads(line)['value']
        stamps=[row.get(key) for key in ('ros_ns','capture_ns','stamp_ns','decision_ros_ns')]
        if not any(type(stamp) is int and near(stamp) for stamp in stamps):continue
        output.write(json.dumps(dict(kind=kind,value=row))+'\n');counts[kind]=counts.get(kind,0)+1
report=dict(scope='original_failure_post_reap_streaming_diagnostic_no_result_promotion',trial=trial,
    source_manifest_sha256=hashlib.sha256((root/'source_manifest.json').read_bytes()).hexdigest(),
    source_observations_sha256=source_sha.hexdigest(),operational_frames=frames,
    unique_joint_captures=len(identities),exceedance_frames=len(bad),
    unique_exceedance_captures=len({r['joint_stamp_ns'] for r in bad}),
    first=bad[0],maximum=maximum,all_exceedances=bad,window_counts=counts,
    original_carry_report=json.loads((root/'carry_hold_assessment.json').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(output=str(out),frames=frames,unique_captures=len(identities),
    exceedance_frames=len(bad),unique_bad=len({r['joint_stamp_ns'] for r in bad}),window_counts=counts,
    first={k:bad[0][k] for k in ('stage','joint_stamp_ns','speed','crawl')},
    maximum={k:maximum[k] for k in ('stage','joint_stamp_ns','speed','crawl')}),indent=2))
