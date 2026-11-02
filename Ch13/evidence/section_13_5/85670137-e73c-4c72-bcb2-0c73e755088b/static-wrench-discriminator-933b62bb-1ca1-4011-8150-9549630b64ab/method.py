"""Closed-state torque/Jacobian balance; no simulator writes or acceptance."""
from pathlib import Path
import hashlib,json,uuid
import xml.etree.ElementTree as ET
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.leg_kinematics import fk_leg,ik_leg

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-gazebo-c6ee257f-512c-487b-9a1f-1f2be2ac05e1'
t=json.loads((trial/'teardown.json').read_text());assert t['parent_reaped'] and not t['residual_live_pids']
r=json.loads((trial/'result.json').read_text());c=json.loads((trial/'controller_report.json').read_text());f=c['first_fault']
model=compile_model(Path(r['scene']['robot']['path']).read_text());assert model.model_sha256==f['model_sha256']
q=f['samples']['joints']['data']['position'];qd=f['samples']['joints']['data']['velocity']
rotation,_=body_rotation(f['samples']['body']['data']);pose=np.eye(4);pose[:3,:3]=rotation;pose[:3,3]=f['samples']['body']['data']['position']
reference=np.asarray(f['reference_body']);inverse=np.linalg.inv(reference);tree=ET.fromstring(model.urdf)
rows=[]
for index,foot in enumerate(model.feet):
    names=[foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf')]
    local=(inverse@np.r_[f['targets'][foot],1.])[:3]
    command=ik_leg(model,foot,local,tuple(q[n] for n in names))
    actual=np.asarray([q[n] for n in names]);jac=np.zeros((3,3));gravity=[];kp=[];damping=[]
    for i,name in enumerate(names):
        delta=np.zeros(3);delta[i]=1e-6
        jac[:,i]=rotation@(np.asarray(fk_leg(model,foot,actual+delta))-fk_leg(model,foot,actual-delta))/(2e-6)
        plus=dict(q);minus=dict(q);plus[name]+=1e-6;minus[name]-=1e-6
        def energy(values):
            return sum(mass*9.81*(pose@model.chains[link].forward(values)@np.r_[origin,1.])[2]
                for link,(mass,origin) in model.masses.items() if link.startswith(foot[:3]))
        gravity.append((energy(plus)-energy(minus))/(2e-6))
        joint=tree.find(f"ros2_control/joint[@name='{name}']")
        kp.append(float(joint.findtext("param[@name='ch13_kp']")))
        damping.append(float(joint.findtext("param[@name='ch13_native_damping']")))
    torque=np.asarray(kp)*(command-actual)
    estimated=np.linalg.solve(jac.T,np.asarray(gravity)-torque+np.asarray(damping)*[qd[n] for n in names])
    last=[c['current']['last_published_leg_targets'][n] for n in names]
    rows.append(dict(foot=foot,estimated_static_force_world_n=estimated.tolist(),
        observed_normal_n=f['samples']['contacts']['data']['forces'][index],
        position_torque_estimate_nm=torque.tolist(),leg_gravity_gradient_nm=gravity,
        reconstructed_command_minus_last_published_rad=(np.asarray(command)-last).tolist()))
out=base/('static-wrench-discriminator-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
v=dict(scope='static_position_servo_estimate_not_measured_actuator_force',trial=trial.name,
    report_sha256=hashlib.sha256((trial/'controller_report.json').read_bytes()).hexdigest(),rows=rows,
    caveats=['omits acceleration and20ms applied-reference lag',
        'foot-center Jacobian omits tangential contact-point lever arm',
        'only this known height fault holds last motor reference; do not reuse after a commanded fault landing',
        'no physical acceptance or command issued'])
(out/'result.json').write_text(json.dumps(v,indent=2,allow_nan=False))
print(json.dumps(dict(output=str(out),**v)),flush=True)
