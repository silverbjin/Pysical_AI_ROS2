"""Preserve all closed-input trials, including first-call deadline failures."""
import hashlib,json,os,sys,time,uuid
from pathlib import Path
repo=Path.cwd();nav=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(nav))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.load_transition import SpatialLoadTransition
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
from integrated_robot_navigation.native_mass import NativeMassEvaluator
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
output=base/('task8-kernel-budget-diagnostic-'+str(uuid.uuid4())+'.json')
fixtures={k:nav/'test/fixtures'/v for k,v in {
    'height':'native_26a3_spatial_budget.json','xyz':'native_c371_xyz_budget.json'}.items()}
cases={k:json.loads(p.read_text()) for k,p in fixtures.items()}
result=dict(scope='closed_input_timing_diagnostic_not_acceptance_or_retry',
    fixture_sha256={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in fixtures.items()},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (nav/'integrated_robot_navigation').glob('*.py')},
    environment={k:os.getenv(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')},
    load_before=Path('/proc/loadavg').read_text().strip(),samples=[])
for kind in ('height','xyz'):
    case=cases[kind];model=compile_model(case['urdf'])
    with NativeMassEvaluator(model) as core:
        variants={'python':SpatialLoadTransition(model),'native':SpatialLoadTransition(model,terms_evaluator=core.contact_terms)} if kind=='height' else {
            'compiled':SpatialXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms)}
        if kind=='xyz':variants['compiled'].prepare()
        for index in range(12):
            for name,kernel in variants.items():
                start=time.perf_counter_ns();cpu=time.thread_time_ns();row=dict(kind=kind,variant=name,index=index)
                try:kernel.step(**case['args']);row['success']=True
                except ValueError as error:row.update(success=False,error=str(error))
                row.update(wall_ns=time.perf_counter_ns()-start,cpu_ns=time.thread_time_ns()-cpu,trace=kernel.last_attempt)
                result['samples'].append(row)
result['load_after']=Path('/proc/loadavg').read_text().strip()
assert not output.exists();output.write_text(json.dumps(result,indent=2))
output.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(output),trials=[{k:v for k,v in r.items() if k!='trace'} for r in result['samples']]),indent=2))
