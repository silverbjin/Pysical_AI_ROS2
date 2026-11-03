import hashlib,json,sys,time,uuid
from pathlib import Path
import numpy as np
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2');n=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(n))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.contact_equilibrium import leg_terms
c=json.loads((n/'test/fixtures/native_da61_contact_age.json').read_bytes());model=compile_model(c['urdf'])
def measured(fn):
 w=time.perf_counter_ns();t=time.thread_time_ns();v=fn();return v,dict(wall_ns=time.perf_counter_ns()-w,thread_ns=time.thread_time_ns()-t)
with NativeMassEvaluator(model) as core:
 a,ta=measured(lambda:leg_terms(model,c['joints'],np.array(c['body']),c['points']))
 b,tb=measured(lambda:core.contact_terms(model,c['joints'],np.array(c['body']),c['points']))
 errors=[max(float(np.max(np.abs(np.asarray(left[f])-right[f]))) for f in model.feet) for left,right in zip(a,b)]
 assert max(errors)<1e-10,errors
 out=dict(scope='one-call current input contact arithmetic comparison, not C1 or causal transport proof',legacy=ta,native=tb,max_jacobian_error=errors[0],max_gravity_error_nm=errors[1],samples_per_condition=1,provenance=core.provenance,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
b=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';p=b/('support-term-reuse-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(out,indent=2))
