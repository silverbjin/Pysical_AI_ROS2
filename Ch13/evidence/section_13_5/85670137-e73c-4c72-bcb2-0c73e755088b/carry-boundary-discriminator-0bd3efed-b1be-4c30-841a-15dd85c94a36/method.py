"""Post-reap numeric correlation; no inferred physics or acceptance credit."""
from pathlib import Path
import hashlib,json,uuid,math
import xml.etree.ElementTree as ET

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
name='native-g2-gazebo-4342c86d-3d22-4577-82bb-6880490c8fb8';trial=base/name
closed=json.loads((trial/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
carry=json.loads((trial/'carry_failure_report.json').read_text());fault=carry['first_fault'];end=fault['ros_ns']
report=json.loads((trial/'controller_report.json').read_text());run=json.loads((trial/'result.json').read_text())
rows=[];previous={};kinds={};sources={}
source=trial/'mission_probe/observations.jsonl'
for line in source.open():
    r=json.loads(line);v=r['value'];stamp=v.get('stamp_ns',-1);kind=r['kind']
    kinds[kind]=kinds.get(kind,0)+1
    if not end-2_000_000_000<=stamp<=end+50_000_000:continue
    if kind not in ('joints','body','contacts','imu','crawl_state'):continue
    data=v.get('data',v);small=dict(kind=kind,stamp_ns=stamp,received_ns=v.get('received_ns'))
    if kind=='joints':
        qd=data['velocity'];small.update(arm_velocity={n:s for n,s in qd.items() if n.startswith('arm_')},
            max_leg_velocity=max(abs(s) for n,s in qd.items() if not n.startswith(('arm_','gripper_'))))
    elif kind=='contacts':small.update(forces=data['forces'])
    elif kind=='body':small.update(position=data['position'],linear_velocity=data['linear_velocity'],angular_velocity=data['angular_velocity'])
    elif kind=='imu':small.update(data)
    else:small.update(data)
    if previous.get(kind)!=stamp:rows.append(small)
    previous[kind]=stamp
commands=report['command_publications']['rows'];names=report['command_publications']['joint_names'];edges=[]
for a,b in zip(commands,commands[1:]):
    if not end-2_000_000_000<=b['decision_ros_ns']<=end:continue
    delta=[y-x for x,y in zip(a['values'],b['values'])];i=max(range(len(delta)),key=lambda i:abs(delta[i]))
    edges.append(dict(ros_ns=b['decision_ros_ns'],dt_ns=b['decision_ros_ns']-a['decision_ros_ns'],
        max_joint=names[i],max_step_rad=delta[i],values=b['values']))
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'native_controls.json'
packets=json.loads(native.read_text())['records'];selected=min(packets,key=lambda r:abs(r['capture_ns']-end))
tree=ET.parse(run['scene']['robot']['path']);gains={}
for j in tree.findall('ros2_control/joint'):
    gains[j.attrib['name']]={p.attrib['name']:p.text for p in j.findall('param')}
out=base/('carry-boundary-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
v=dict(scope='closed_original_observers_and_nearby_native_packet_not_exact_sync',trial=name,fault=fault,
    input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,native,trial/'controller_report.json')},
    rows=rows,command_edges=edges,nearest_native_packet=selected,gains=gains,kinds=kinds)
(out/'result.json').write_text(json.dumps(v,indent=2,allow_nan=False))
arms=[r for r in rows if r['kind']=='joints'];bodies=[r for r in rows if r['kind']=='body']
summary=dict(output=str(out),kinds=kinds,unique_arm_captures=len(arms),
    first_arm_violation=next((r for r in arms if max(abs(s) for s in r['arm_velocity'].values())>.02),None),
    largest_command_edge=max(edges,key=lambda r:abs(r['max_step_rad']),default=None),
    body_max_linear_speed=max((math.sqrt(sum(s*s for s in r['linear_velocity'])) for r in bodies),default=None),
    native_capture_ns=selected['capture_ns'],native_joints=[j for j in selected['joints'] if j['name'].startswith('arm_')])
print(json.dumps(summary),flush=True)
