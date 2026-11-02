"""Same exact candidate, interleaved original/batched geometry and full kernel."""
import sys,json,time,hashlib,statistics
from pathlib import Path
import numpy as np
root=Path.cwd();src=root/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(src))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
from integrated_robot_navigation.reference_envelope import reference_constraints
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
base=root/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
fixture=src/'test/fixtures/native_c371_xyz_budget.json';case=json.loads(fixture.read_text())
old_profile=json.loads((base/'task8-c371-geometry-profile-01.json').read_text())
model=compile_model(case['urdf']);a=case['args'];limits=case['limits']
targets={f:np.array(a['reference_xyz'][f])+old_profile['kernel_delta'][f] for f in model.feet}
args=dict(joints=a['joints'],body=a['reference_pose'],targets=targets,envelope=a['allowed_z'],
    selected=a['foot'],future_targets=a['future_targets'])
evaluator=CompiledReferenceEnvelope(model,limits);samples=[];maximum_error=0.
for index in range(24):
    row={};outputs={}
    for name in (('original','batch') if index%2==0 else ('batch','original')):
        start=time.perf_counter_ns();cpu=time.thread_time_ns()
        outputs[name]=(evaluator.evaluate(**args) if name=='batch' else reference_constraints(model,limits,**args))
        row[name]=dict(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu)
    x,y=outputs['original'],outputs['batch']
    error=max(max(abs(x[0][n]-y[0][n]) for n in x[0]),float(np.max(np.abs(x[1]-y[1]))),float(np.max(np.abs(x[2]-y[2]))))
    assert error<2e-12;maximum_error=max(maximum_error,error);samples.append(row)
kernel_samples=[]
with NativeMassEvaluator(model) as core:
    kernel=SpatialXYZTransition(model,limits,terms_evaluator=core.contact_terms);kernel.prepare()
    for index in range(24):
        record=dict(index=index)
        try:record['delta']=kernel.step(**a);record['prediction']=kernel.last_model
        except ValueError as error:record['error']=str(error)
        record['trace']=kernel.last_attempt;kernel_samples.append(record)
out=dict(scope='closed_exact_candidate_comparison_not_engine_success',geometry_samples=samples,
    maximum_residual_difference=maximum_error,kernel_samples=kernel_samples,
    kernel_failures=sum('error' in v for v in kernel_samples),
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'integrated_robot_navigation').glob('*.py')})
output=base/'task8-c371-batch-comparison-01.json';assert not output.exists();output.write_text(json.dumps(out,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(output),maximum_residual_difference=maximum_error,
    median_geometry_wall_ns={name:statistics.median(row[name]['wall_ns'] for row in samples) for name in ('original','batch')},
    kernel_failures=out['kernel_failures'],kernel_wall_ns=[v['trace']['stages'].get('exact_ik_validated',{}).get('wall_ns') for v in kernel_samples])))
raise SystemExit(bool(out['kernel_failures']))
