"""Interleaved before/after math costs, not native engine acceptance."""
import hashlib,importlib.util,json,os,statistics,sys,time,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.projection import body_rotation
repo=Path.cwd();base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'native-g2-mujoco-17c2e988-3231-4c8b-849d-438c982bfe14'
closed=json.loads((trial/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((trial/'controller_report.json').read_text());result=json.loads((trial/'result.json').read_text())
model=compile_model(Path(result['scene']['robot']['path']).read_text())
samples=report['first_fault']['samples'];q=samples['joints']['data']['position']
pose=np.eye(4);pose[:3,:3]=body_rotation(samples['body']['data'])[0];pose[:3,3]=samples['body']['data']['position']
files=dict(before=base/'static-mass-plan-baseline-support.py',
    after=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/support.py')
functions={}
for key,path in files.items():
    spec=importlib.util.spec_from_file_location('integrated_robot_navigation._mass_benchmark_'+key,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);functions[key]=module.center_of_mass
expected=functions['before'](model,q,pose);actual=functions['after'](model,q,pose)
assert np.allclose(expected,actual,atol=2e-12,rtol=0.)
costs={key:dict(wall=[],cpu=[]) for key in files}
for _ in range(200):
    for key,callback in functions.items():
        wall=time.perf_counter_ns();cpu=time.thread_time_ns();callback(model,q,pose)
        costs[key]['cpu'].append(time.thread_time_ns()-cpu)
        costs[key]['wall'].append(time.perf_counter_ns()-wall)
stats={key:{kind:dict(median_ns=statistics.median(values),mean_ns=statistics.mean(values),max_ns=max(values))
    for kind,values in kinds.items()} for key,kinds in costs.items()}
out=base/('benchmark-static-mass-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
value=dict(scope='offline_interleaved_actual_state_math_not_engine_or_timing_acceptance',uid=os.getuid(),
    report_sha256=hashlib.sha256((trial/'controller_report.json').read_bytes()).hexdigest(),
    source_hashes={key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in files.items()},
    results=dict(before=expected,after=actual,max_error=float(np.max(np.abs(np.asarray(expected)-actual)))),
    samples_per_version=200,stats=stats,environment={key:os.environ.get(key)
        for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','LP_NUM_THREADS')})
(out/'result.json').write_text(json.dumps(value,indent=2));print(json.dumps(dict(path=str(out),**value)),flush=True)
