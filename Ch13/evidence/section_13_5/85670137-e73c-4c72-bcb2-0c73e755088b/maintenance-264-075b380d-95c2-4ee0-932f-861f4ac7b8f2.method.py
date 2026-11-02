"""Counterfactual safety on recorded states, NOT a physical replay success."""
import copy,hashlib,json,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
from integrated_robot_navigation.projection import body_rotation
r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
fp=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_ab85_infeasible.json'
c=json.loads(fp.read_bytes());m=compile_model(c['urdf']);a=c['args']
raw=b/c['provenance']['trial']/'all_frames.json';frames=json.loads(raw.read_bytes())['frames']
targets=copy.deepcopy(a['reference_xyz']);rows=[];snapshots=[]
with NativeMassEvaluator(m) as mass:
 k=CompleteXYZTransition(m,c['limits'],native_mass=mass)
 try:
  k.prepare()
  for cutoff in (56940000000,56960000000,56980000000,56990000000):
   frame=next(f for f in frames if f['ros_ns']>=cutoff);samples=frame['samples']
   body=samples['body']['data'];pose=np.eye(4);pose[:3,:3]=body_rotation(body)[0];pose[:3,3]=body['position']
   current=copy.deepcopy(a);current.update(joints=samples['joints']['data']['position'],body_pose=pose.tolist(),
    points=dict(zip(m.feet,samples['contacts']['data']['points'])),
    forces_world=dict(zip(m.feet,samples['contacts']['data']['forces_world'])),reference_xyz=copy.deepcopy(targets),dt=.02)
   command,_,_=k.geometry.evaluate(joints=current['joints'],body=np.array(a['reference_pose']),targets=targets,
    envelope=a['allowed_z'],selected=a['foot'],future_targets=a['future_targets'])
   current['command_joints']=dict(current['joints']);current['command_joints'].update(command)
   maintenance=cutoff<56990000000
   if maintenance:
    current['target_forces']=copy.deepcopy(current['forces_world'])
    z=targets[a['foot']][2];current['allowed_z'][a['foot']]=[z,z]
    current['future_targets'][a['foot']]=copy.deepcopy(targets[a['foot']])
   snapshots.append({'ros_ns':frame['ros_ns'],'samples':samples,'args':current,'maintenance':maintenance})
   try:
    delta=k.step(**current)
    targets={f:(np.array(targets[f])+delta[f]).tolist() for f in m.feet}
    rows.append({'ros_ns':frame['ros_ns'],'maintenance':maintenance,'passed':True,'delta':delta,
     'fl_calf_servo_nm':k.last_model['predicted_servo_command_efforts']['fl_calf_joint'],
     'iterations':k.last_model['optimization_iterations']})
   except ValueError as error:
    rows.append({'ros_ns':frame['ros_ns'],'maintenance':maintenance,'passed':False,'error':str(error)});break
 finally:k.close()
out={'scope':'counterfactual_candidates_on_recorded_states_not_physical_closed_loop_or_success',
 'fixture_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
 'rows':rows,'snapshots':snapshots,'urdf':c['urdf'],'limits':c['limits']}
target=b/('maintenance-264-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps({'path':str(target),'rows':rows},indent=2))
