"""Offline original-success/current-consumption boundary diagnosis; no commands."""
import hashlib,json,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
from integrated_robot_navigation.native_reference import NativeReferenceEnvelope

r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=b/'native-contact-component-gazebo-dbdfa89a-17bf-457f-9f6a-a049f25ca718'
rp=trial/'controller_report.json';report=json.loads(rp.read_bytes());fault=report['first_fault']
v=fault['load_transfer_observation'];assert v['numeric_input_job_id']==v['worker']['last_input_id']==v['worker']['last_reply']['id']==325
assert v['worker']['last_reply']['ok'] is True
prior=json.loads((r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_141b_xyz_budget.json').read_bytes())
assert hashlib.sha256(prior['urdf'].encode()).hexdigest()==report['model_sha256']
profile=json.loads((trial/'validated_profile.json').read_bytes());assert prior['limits']==profile['limits']
c={'scope':'successful_numeric_reply_rejected_by_current_parent_not_failed_numeric_job',
 'urdf':prior['urdf'],'limits':profile['limits'],'args':v['numeric_input'],
 'parent':{'fault':fault,'report_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()},
 'provenance':{'job_id':325,'trial':trial.name,'last_reply':v['worker']['last_reply']}}
fp=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_dbdf_current_servo.json'
if fp.exists():assert json.loads(fp.read_bytes())==c
else:fp.write_text(json.dumps(c,indent=2))
m=compile_model(c['urdf']);a=c['args'];current=fault['samples']['joints']['data']['position']
with NativeMassEvaluator(m) as mass:
 k=CompleteXYZTransition(m,c['limits'],native_mass=mass)
 try:
  k.prepare();delta=k.step(**a);proposed={f:np.array(a['reference_xyz'][f])+delta[f] for f in m.feet}
  with NativeReferenceEnvelope(m,c['limits']) as geom:
   exact,clear,bounds=geom.evaluate(joints=current,body=np.array(a['reference_pose']),targets=proposed,
    envelope=a['allowed_z'],selected=a['foot'],future_targets=a['future_targets'])
  rows=[]
  for n in m.joint_names:
   gain=k.gains[n];old=a['joints'][n];q=current[n]
   rows.append({'joint':n,'limit_nm':m.limits[n][3],'original_servo_nm':gain*(exact[n]-old),
    'current_servo_nm':gain*(exact[n]-q),'joint_motion_rad':q-old,
    'velocity_rad_s':fault['samples']['joints']['data']['velocity'][n],
    'reference_servo_nm':gain*(a['command_joints'][n]-q),
    'torque_drift_nm':gain*(old-q)})
  out={'scope':'offline_parent_consumption_proof_not_engine_acceptance','fixture_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),
   'job_id':325,'selected':a['foot'],'original_snapshot':v['original_snapshot']['samples']['joints'],
   'current_snapshot':{key:fault['samples']['joints'][key] for key in ('stamp_ns','received_ns')},
   'current_kernel_original_input_passed':True,'rows':rows,'delta':{f:list(d) for f,d in delta.items()},
   'native_model':k.last_model}
 finally:k.close()
target=b/('current-servo-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(target),'fixture':str(fp),'sha256':out['fixture_sha256'],'rows':sorted(rows,key=lambda row:-(abs(row['current_servo_nm'])-row['limit_nm']))[:4]}))
