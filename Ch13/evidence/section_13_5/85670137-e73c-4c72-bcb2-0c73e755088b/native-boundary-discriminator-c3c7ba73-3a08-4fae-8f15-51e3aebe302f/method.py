"""One bounded original native packet near a closed fault; preserve its phase."""
from pathlib import Path
import json,hashlib,uuid
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.projection import body_rotation
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
name='native-g2-gazebo-c6ee257f-512c-487b-9a1f-1f2be2ac05e1';copy=base/name
t=json.loads((copy/'teardown.json').read_text());assert t['parent_reaped'] and not t['residual_live_pids']
f=json.loads((copy/'controller_report.json').read_text())['first_fault'];r=json.loads((copy/'result.json').read_text())
source=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/name/'native_controls.json'
rows=json.loads(source.read_text())['records'];packet=min(rows,key=lambda a:abs(a['capture_ns']-f['ros_ns']))
model=compile_model(Path(r['scene']['robot']['path']).read_text());rotation,_=body_rotation(f['samples']['body']['data'])
native={j['name']:j for j in packet['joints']};body=f['samples']['body']['data'];points=packet['body_references'][-1]['raw_contacts']['feet'];comparisons=[]
for foot in model.feet:
    q=[native[foot[:2]+'_'+part+'_joint']['position'] for part in ('hip','thigh','calf')]
    predicted=rotation@fk_leg(model,foot,q)+body['position']
    point=next(p for p in points if p['name']==foot)
    comparisons.append(dict(foot=foot,urdf_fk_world=predicted.tolist(),native_center=point['center_world'],
        error_m=float(np.linalg.norm(predicted-point['center_world']))))
out=base/('native-boundary-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
v=dict(scope='post_reap_original_packet_and_nearby_pose_not_exact_time_aligned',trial=name,
    packet=packet,input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),comparisons=comparisons,
    pose_capture_ns=f['samples']['body']['stamp_ns'],joint_state_capture_ns=packet['state_capture_ns'])
(out/'result.json').write_text(json.dumps(v,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),comparisons=comparisons,body_reference_keys=list(packet['body_references'][-1]))),flush=True)
