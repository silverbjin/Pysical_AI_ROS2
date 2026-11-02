"""Interleaved isolated processes at one actual failed state, no engine/ROS init."""
import hashlib,json,os,statistics,subprocess,sys,time,uuid
from pathlib import Path

def worker(root):
    import numpy as np
    from integrated_robot_navigation.model import compile_model
    from integrated_robot_navigation.gait import CrawlMachine
    from integrated_robot_navigation.samples import Sample,SensorBundle
    from integrated_robot_navigation.support import center_of_mass
    from integrated_robot_navigation.projection import body_rotation
    report=json.loads((root/'controller_report.json').read_text());result=json.loads((root/'result.json').read_text())
    model=compile_model(Path(result['scene']['robot']['path']).read_text())
    assert model.model_sha256==report['model_sha256']
    fault=report['first_fault'];samples=fault['samples']
    bundle=SensorBundle(**{key:Sample(**value) if value else None for key,value in samples.items()})
    q=samples['joints']['data']['position'];pose=np.eye(4)
    pose[:3,:3]=body_rotation(samples['body']['data'])[0];pose[:3,3]=samples['body']['data']['position']
    machine=CrawlMachine(model,json.loads((root/'validated_profile.json').read_text())['limits'])
    machine.state='CRAWL'
    machine.reference_body=np.asarray(fault['reference_body'])
    machine._targets={name:np.asarray(value) for name,value in fault['targets'].items()}
    machine.offset=np.zeros(2)
    def measure():return machine._measure(bundle,fault['ros_ns'],fault['wall_ns'])
    def solve():return machine._solve(q,True)
    def mass():return center_of_mass(model,q,pose)
    def combined():measure();return solve()
    functions=dict(mass=mass,measure=measure,solve=solve,combined=combined)
    expected=dict(mass=mass(),targets=solve())
    for _ in range(20):combined()
    costs={key:dict(wall=[],cpu=[]) for key in functions}
    for _ in range(200):
        for key,callback in functions.items():
            wall=time.perf_counter_ns();cpu=time.thread_time_ns();callback()
            costs[key]['cpu'].append(time.thread_time_ns()-cpu);costs[key]['wall'].append(time.perf_counter_ns()-wall)
    def stats(values):return dict(mean_ns=statistics.mean(values),median_ns=statistics.median(values),max_ns=max(values))
    pools=None
    try:
        from threadpoolctl import threadpool_info
        pools=threadpool_info()
    except ImportError:pass
    return dict(model_sha256=model.model_sha256,report_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
        numpy=np.__version__,thread_count=len(list(Path('/proc/self/task').iterdir())),pools=pools,
        environment={key:os.environ.get(key) for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','LP_NUM_THREADS')},
        results=expected,stats={key:{kind:stats(values) for kind,values in kinds.items()} for key,kinds in costs.items()})

if sys.argv[1]=='--worker':
    print(json.dumps(worker(Path(sys.argv[2]))));raise SystemExit(0)
root=Path(sys.argv[1]);base=Path(sys.argv[2]);closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
out=base/('math-thread-benchmark-'+str(uuid.uuid4()));out.mkdir();trials=[]
(out/'method.py').write_bytes(Path(__file__).read_bytes())
for index,mode in enumerate(('inherited','blas1','blas1','inherited')):
    env=dict(os.environ)
    if mode=='blas1':env['OPENBLAS_NUM_THREADS']='1'
    command=[sys.executable,str(Path(__file__).resolve()),'--worker',str(root)]
    child=subprocess.run(command,env=env,capture_output=True,text=True)
    (out/f'child-{index}.stderr').write_text(child.stderr)
    if child.returncode:
        (out/'failure.json').write_text(json.dumps(dict(command=command,returncode=child.returncode,stderr=child.stderr)))
        raise SystemExit(child.stderr)
    value=json.loads(child.stdout);trials.append(dict(mode=mode,**value))
    (out/'progress.json').write_text(json.dumps(trials,indent=2))
assert all(trial['results']==trials[0]['results'] for trial in trials)
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,trials=trials,numerically_identical=True),indent=2))
print(json.dumps(dict(output=str(out),trials=[{k:v for k,v in trial.items() if k not in ('results','report_sha256')} for trial in trials])))
