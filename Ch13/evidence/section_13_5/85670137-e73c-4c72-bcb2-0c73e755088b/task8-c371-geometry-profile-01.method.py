"""Exact submitted input extraction and closed geometry-only cost profile."""
import sys,json,time,hashlib,copy,cProfile,pstats,io
from pathlib import Path
import numpy as np
root=Path.cwd();src=root/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(src))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import load_scene
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation import load_xyz as module
base=root/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-contact-component-gazebo-c3719b6e-a20f-43a2-b8bf-2edeb0353737'
report_path=trial/'controller_report.json';r=json.loads(report_path.read_text())
obs=r['first_fault']['load_transfer_observation'];args=obs['numeric_input']
prepared=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g1-gazebo-47892299-1722-4a76-acdb-942585899d39-prepared')
scene=load_scene('gazebo',prepared/'scene');urdf=Path(scene['robot']['path']).read_text()
model=compile_model(urdf);assert model.model_sha256==r['model_sha256']
limits=json.loads((prepared/'carry_profile.json').read_text())['limits']
fixture=dict(scope='exact_numeric_job_not_later_parent_snapshot',urdf=urdf,args=args,limits=limits,
    original_snapshot=obs['original_snapshot'],failure_attempt=obs['attempt'],
    report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    source_manifest_sha256=hashlib.sha256((trial/'source_manifest.json').read_bytes()).hexdigest(),
    install_manifest_sha256=hashlib.sha256((trial/'install_manifest.json').read_bytes()).hexdigest())
case=src/'test/fixtures/native_c371_xyz_budget.json';assert not case.exists();case.write_text(json.dumps(fixture,indent=2))
actual=module.reference_constraints;captured=[]
def capture(*a,**kw):
    captured.append((a,kw));return actual(*a,**kw)
module.reference_constraints=capture
result=dict(scope='closed_exact_input_geometry_profile_not_physical_success',
    fixture_sha256=hashlib.sha256(case.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
with NativeMassEvaluator(model) as core:
    kernel=module.SpatialXYZTransition(model,limits,terms_evaluator=core.contact_terms);kernel.prepare()
    try:result['kernel_delta']=kernel.step(**args)
    except ValueError as error:result['kernel_error']=str(error)
    result['kernel_attempt']=kernel.last_attempt
assert len(captured)==1, 'geometry not reached: preserve failure and investigate preceding stage'
a,kw=captured[0];times=[]
for _ in range(24):
    start=time.perf_counter_ns();cpu=time.thread_time_ns();q,clear,bounds=actual(*a,**kw)
    times.append(dict(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu))
result.update(geometry_samples=times,nominal_joints=q,minimum_clearance=float(min(clear)),minimum_joint_margin=float(min(bounds)))
prof=cProfile.Profile();prof.enable()
for _ in range(100):actual(*a,**kw)
prof.disable();stream=io.StringIO();pstats.Stats(prof,stream=stream).sort_stats('cumulative').print_stats(20)
result['profile_top20']=stream.getvalue()
output=base/'task8-c371-geometry-profile-01.json';assert not output.exists();output.write_text(json.dumps(result,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(artifact=str(output),kernel_error=result.get('kernel_error'),
    geometry_wall_ns=[t['wall_ns'] for t in times],profile_top20=result['profile_top20']),indent=2))
