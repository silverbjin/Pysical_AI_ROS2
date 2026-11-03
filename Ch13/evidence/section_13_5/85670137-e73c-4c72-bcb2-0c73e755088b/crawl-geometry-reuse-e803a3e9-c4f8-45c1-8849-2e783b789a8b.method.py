import hashlib,json,sys,time,uuid
from pathlib import Path
import numpy as np
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2');n=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(n))
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.reference_envelope import reference_constraints
c=json.loads((n/'test/fixtures/native_da61_contact_age.json').read_bytes());model=compile_model(c['urdf'])
mass=NativeMassEvaluator(model);old=CrawlMachine(model,c['limits']);new=CrawlMachine(model,c['limits'],mass_evaluator=mass,load_transfer_policy='coupled_contact',async_load_transfer=True,load_result_timing='same_cycle',load_receipt_mode='event_receiver')
for m in (old,new):
 m.state='CRAWL';m.reference_body=np.array(c['body']);m._targets={f:np.array(p) for f,p in c['targets'].items()};m.planning_reference_envelope=c['envelope']
def measured(fn):
 w=time.perf_counter_ns();t=time.thread_time_ns();value=fn();return value,dict(wall_ns=time.perf_counter_ns()-w,thread_ns=time.thread_time_ns()-t)
try:
 a,ta=measured(lambda:old._solve(c['joints'],True));d,td=measured(lambda:new._solve(c['joints'],True))
 names=model.joint_names;np.testing.assert_allclose([a[n] for n in names],[d[n] for n in names],atol=2e-12,rtol=0.)
 args=dict(joints=c['joints'],body=np.array(c['body']),targets=c['targets'],selected=new.ORDER[0],future_targets=c['targets'])
 x,tx=measured(lambda:reference_constraints(model,c['limits'],envelope=c['envelope'],**args));y,ty=measured(lambda:new._reference_constraints(**args))
 for left,right in zip(x[1:],y[1:]):np.testing.assert_allclose(left,right,atol=2e-12,rtol=0.)
 np.testing.assert_allclose([x[0][n] for n in names],[y[0][n] for n in names],atol=2e-12,rtol=0.)
 out=dict(scope='one-call geometry arithmetic comparison; not transport-cause proof or C1 acceptance',nominal_python=ta,nominal_native=td,full28_python=tx,full28_native=ty,arithmetic_parity=True,samples_per_condition=1,reuses_same_handle=new._kinematics_evaluator is new._reference_geometry,source_sha256=hashlib.sha256((n/'integrated_robot_navigation/gait.py').read_bytes()).hexdigest(),method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 b=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';p=b/('crawl-geometry-reuse-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(out,indent=2))
finally:new.close_load_transfer();mass.close()
