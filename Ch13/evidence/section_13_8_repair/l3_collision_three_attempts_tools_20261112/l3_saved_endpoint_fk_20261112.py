import json,tarfile,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from ch13_piper_moveit_config.configuration import parameters
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.model import urdf_fk
from ch13_system_validation.scenarios import get_scenario,grasp_pose
root=Path.cwd();case=root/'Ch13/evidence/section_13_8_system/e475ece0-9f70-4dae-8de9-491ee92c95fc'
with tarfile.open(case/'raw.tar.gz') as t:
 pick=json.load(t.extractfile('pick_mission.json'));ns=next(r['clock_ns'] for r in pick['stages'] if r.get('phase')=='PRE_GRASP')
 samples=[json.loads(x) for x in t.extractfile('engine_observations.jsonl')];anchor=min(samples,key=lambda r:abs(r['sim_s']-ns/1e9))
 obs=[json.loads(x) for x in t.extractfile('vision_observations.jsonl')];obs=max((r for r in obs if 'point' in r and r.get('capture_ns',0)<=ns),key=lambda r:r['capture_ns'])
q=np.array(anchor['qpos']);center=np.array(obs['point']);forward=center-np.array([*q[:2],center[2]]);forward/=np.linalg.norm(forward)
model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
values={model.joint(j).name:float(q[model.jnt_qposadr[j]]) for j in range(model.njnt) if model.jnt_type[j]!=0}
description=parameters()['robot_description'];base=np.eye(4);base[:3,3]=q[:3];base[:3,:3]=Rotation.from_quat(q[[4,5,6,3]]).as_matrix()
report=[]
for sign,p in zip((1.,-1.),(r for r in pick['planning'] if r.get('kind')=='plan')):
 traj=p['trajectory']['joint_trajectory'];v=dict(values);v.update(zip(traj['joint_names'],traj['points'][-1]['positions']))
 tcp=base@urdf_fk(description,v)['reuse/tcp'];pre,rot=grasp_pose(center,forward,sign,get_scenario('level3_house'))
 report.append(dict(sign=sign,position_error_m=float(np.linalg.norm(tcp[:3,3]-pre)),orientation_error_rad=float(Rotation.from_matrix(rot.as_matrix().T@tcp[:3,:3]).magnitude()),goal_joints=traj['points'][-1]['positions']))
print(json.dumps(report))