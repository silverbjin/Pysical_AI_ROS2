"""Exact successful numeric input rejected by parent; no engine or command."""
import hashlib,json,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_complete_xyz import CompleteXYZTransition
r=Path.cwd();b=r/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
p=b/'native-contact-component-gazebo-59873b32-4ac9-4451-9950-2175cb256e42'
report=json.loads((p/'controller_report.json').read_bytes());v=report['first_fault']['load_transfer_observation']
assert v['numeric_input_job_id']==v['worker']['last_input_id']==v['worker']['last_reply']['id']==57
assert v['worker']['last_reply']['ok'] is True and v['worker']['fault']==''
old=json.loads((r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_141b_xyz_budget.json').read_bytes())
profile=json.loads((p/'validated_profile.json').read_bytes())
assert hashlib.sha256(old['urdf'].encode()).hexdigest()==report['model_sha256']==profile['model_sha256']
case={'scope':'exact_success_numeric_parent_bounds_rejection_not_task_success',
 'urdf':old['urdf'],'limits':profile['limits'],'args':v['numeric_input'],
 'provenance':{'trial':p.name,'job_id':57,'original_snapshot':v['original_snapshot'],
    'reason':report['first_fault']['reason'],'source_sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest()
        for n in ('controller_report.json','validated_profile.json','source_manifest.json','install_manifest.json')}}}
fixture=r/'Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_5987_parent_bounds.json'
with fixture.open('x') as f:json.dump(case,f,indent=2)
model=compile_model(case['urdf']);a=case['args'];checks={}
with NativeMassEvaluator(model) as core:
 kernel=CompleteXYZTransition(model,case['limits'],native_mass=core)
 try:
  kernel.prepare();delta=kernel.step(**a)
  for foot in model.feet:
   d=np.asarray(delta[foot]);proposed=np.asarray(a['reference_xyz'][foot])+d
   lo,hi=a['allowed_z'][foot];distance=float(np.linalg.norm(proposed-a['origins'][foot]))
   checks[foot]={'delta':d.tolist(),'proposed_z':float(proposed[2]),'envelope':[lo,hi],
    'distance_m':distance,'max_distance_m':case['limits']['max_unload_height_m'],
    'distance_ok':bool(distance<=case['limits']['max_unload_height_m']+1e-12),
    'height_ok':bool(lo-1e-12<=proposed[2]<=hi+1e-12),
    'selected_direction_ok':bool(foot!=a['foot'] or np.max(np.abs(d[:2]))<=1e-12 and d[2]>=0.)}
  out={'scope':'exact_parent_bounds_predicates_not_physical_success','fixture':str(fixture),
   'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'job_id':57,
   'checks':checks,'numeric_model':kernel.last_model,'attempt':kernel.last_attempt}
 finally:kernel.close()
target=b/('parent-bounds-'+str(uuid.uuid4())+'.json');target.write_text(json.dumps(out,indent=2))
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'path':str(target),'fixture_sha256':out['fixture_sha256'],'checks':checks}))
