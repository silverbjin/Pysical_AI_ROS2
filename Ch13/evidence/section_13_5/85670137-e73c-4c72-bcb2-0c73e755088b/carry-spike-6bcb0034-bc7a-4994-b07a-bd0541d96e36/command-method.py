"""Correlate recorded actuator reference steps with the original carry spike."""
import json,hashlib
from pathlib import Path
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/'carry-spike-6bcb0034-bc7a-4994-b07a-bd0541d96e36'
summary=json.loads((root/'summary.json').read_text());at=summary['first']['joint_stamp_ns']
rows=[json.loads(line) for line in (root/'window.jsonl').open()]
native=[row['value'] for row in rows if row['kind']=='native_controls'];changes=[]
for previous,current in zip(native,native[1:]):
    old={a['joint_name']:a for a in previous['actuators']}
    delta={a['joint_name']:a['ctrl']-old[a['joint_name']]['ctrl'] for a in current['actuators']}
    leg={k:v for k,v in delta.items() if k[:3] in ('fr_','fl_','rr_','rl_')}
    names=sorted(leg,key=lambda k:abs(leg[k]),reverse=True)
    changes.append(dict(capture_ns=current['capture_ns'],relative_ms=(current['capture_ns']-at)/1e6,
        sample_interval_ms=(current['capture_ns']-previous['capture_ns'])/1e6,
        largest_joint=names[0],largest_delta=leg[names[0]],delta=delta,
        gripper=[{k:a[k] for k in ('joint_name','ctrl','position','velocity','actuator_force','kp','kv')}
                 for a in current['actuators'] if a['joint_name'].startswith('gripper_')],
        body_reference=current['body_reference']))
before=[row for row in changes if -300<=row['relative_ms']<=0]
result=dict(scope='recorded_native_actuator_samples_not_unobserved_publish_timestamps',at=at,
    native_reference_changes=changes,
    largest_before_spike=sorted(before,key=lambda r:abs(r['largest_delta']),reverse=True)[:5],
    source_window_sha256=hashlib.sha256((root/'window.jsonl').read_bytes()).hexdigest())
(root/'command-window.json').write_text(json.dumps(result,indent=2))
(root/'command-method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(at=at,largest=[{k:r[k] for k in ('relative_ms','sample_interval_ms','largest_joint','largest_delta')}
    for r in result['largest_before_spike']],gripper_ctrls=sorted({a['ctrl'] for r in changes for a in r['gripper']})),indent=2))
