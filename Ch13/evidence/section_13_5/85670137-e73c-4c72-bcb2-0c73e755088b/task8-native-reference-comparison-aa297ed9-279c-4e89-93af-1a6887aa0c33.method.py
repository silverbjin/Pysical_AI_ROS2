"""Fixed-input geometry parity/cost, retaining every kernel trial and failure."""
import hashlib,json,sys,time,statistics,uuid
from pathlib import Path
import numpy as np
repo=Path.cwd();nav=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(nav))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
from integrated_robot_navigation.compiled_reference import CompiledReferenceEnvelope
from integrated_robot_navigation.reference_envelope import reference_constraints
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
out=dict(scope='closed_exact_input_geometry_cost_not_engine_or_consecutive_acceptance',cases=[])
for name in ('native_c371_xyz_budget.json','native_8d4f_xyz_budget.json'):
    path=nav/'test/fixtures'/name;case=json.loads(path.read_text());model=compile_model(case['urdf']);a=case['args']
    record=dict(fixture=name,fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),kernel_trials=[],geometry_trials=[])
    with NativeMassEvaluator(model) as core, NativeReferenceEnvelope(model,case['limits']) as native:
        kernel=SpatialXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms);kernel.prepare()
        compiled=CompiledReferenceEnvelope(model,case['limits'])
        try:
            for i in range(24):
                row=dict(index=i)
                try:row['delta']=kernel.step(**a)
                except ValueError as error:row['error']=str(error)
                row['trace']=kernel.last_attempt;record['kernel_trials'].append(row)
            # Geometry point is the exact submitted reference, not a later pose
            # or a chosen passing numeric candidate. All methods get the SAME point.
            args=dict(joints=a['joints'],body=a['reference_pose'],targets=a['reference_xyz'],envelope=a['allowed_z'],
                selected=a['foot'],future_targets=a['future_targets'])
            for i in range(24):
                outputs={};row={}
                for mode in (('original','compiled','native') if i%2==0 else ('native','compiled','original')):
                    start=time.perf_counter_ns();cpu=time.thread_time_ns()
                    outputs[mode]=(reference_constraints(model,case['limits'],**args) if mode=='original' else
                        (compiled if mode=='compiled' else native).evaluate(**args))
                    row[mode]=dict(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu)
                first=outputs['original'];error=0.
                for value in outputs.values():
                    error=max(error,max(abs(first[0][n]-value[0][n]) for n in first[0]),
                        float(np.max(np.abs(first[1]-value[1]))),float(np.max(np.abs(first[2]-value[2]))))
                row['maximum_residual_difference']=error;record['geometry_trials'].append(row)
            record['native_geometry']=native.provenance;record['native_mass']=core.provenance
        finally:kernel.close()
    out['cases'].append(record)
out['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
out['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (nav/'integrated_robot_navigation').glob('*.py')}
cpp=repo/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors/src/reference_geometry.cpp'
out['cpp_sha256']=hashlib.sha256(cpp.read_bytes()).hexdigest()
output=base/('task8-native-reference-comparison-'+str(uuid.uuid4())+'.json')
assert not output.exists();output.write_text(json.dumps(out,indent=2));output.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
summary=[]
for r in out['cases']:
    summary.append(dict(fixture=r['fixture'],failures=sum('error' in v for v in r['kernel_trials']),
        kernel_wall_ns=[v['trace']['stages'].get('exact_ik_validated',{}).get('wall_ns') for v in r['kernel_trials']],
        geometry_median_ns={m:statistics.median(v[m]['wall_ns'] for v in r['geometry_trials']) for m in ('original','compiled','native')},
        maximum_residual_difference=max(v['maximum_residual_difference'] for v in r['geometry_trials'])))
print(json.dumps(dict(path=str(output),summary=summary),indent=2))
raise SystemExit(any(r['failures'] or r['maximum_residual_difference']>2e-12 for r in summary))
