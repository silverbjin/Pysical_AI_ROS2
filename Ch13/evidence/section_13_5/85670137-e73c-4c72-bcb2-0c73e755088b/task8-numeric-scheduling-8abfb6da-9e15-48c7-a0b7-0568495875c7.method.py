"""One bounded scheduling hypothesis, zero engines/commands/system writes."""
import argparse,hashlib,json,os,resource,select,subprocess,sys,time,uuid
from pathlib import Path
repo=Path.cwd();nav=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';sys.path.insert(0,str(nav))
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.load_xyz import SpatialXYZTransition
parser=argparse.ArgumentParser();parser.add_argument('--kernel',choices=('slsqp','native'),default='slsqp');options=parser.parse_args()
task=Path(__file__).parent;fixture=nav/'test/fixtures/native_141b_xyz_budget.json';case=json.loads(fixture.read_text())
mask=sorted(os.sched_getaffinity(0));assert len(mask)>=4;reserved=mask[-1];others=mask[:-1]
def stats():
    r=resource.getrusage(resource.RUSAGE_THREAD)
    return dict(schedstat=[int(v) for v in Path('/proc/thread-self/schedstat').read_text().split()],
        voluntary=r.ru_nvcsw,involuntary=r.ru_nivcsw,major_faults=r.ru_majflt,minor_faults=r.ru_minflt,
        raw_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW),cpu_ns=time.thread_time_ns())
out=dict(scope='closed_input_controlled_CPU_contention_not_actual_engine_or_admission',kernel=options.kernel,original_affinity=mask,
    reserved_cpu=reserved,background_processes=len(others),threads=len(list(Path('/proc/self/task').iterdir())),
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),modes=[])
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';path=base/('task8-numeric-scheduling-'+str(uuid.uuid4())+'.json')
assert not path.exists();path.write_text(json.dumps(out,indent=2))
path.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
path.with_suffix('.background.py').write_bytes((task/'cpu-contention-worker.py').read_bytes())
print(json.dumps(dict(artifact=str(path),pid=os.getpid(),scope=out['scope'])),flush=True)
model=compile_model(case['urdf'])
with NativeMassEvaluator(model) as core:
    if options.kernel=='native':
        from integrated_robot_navigation.native_xyz import NativeXYZTransition
        kernel=NativeXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms)
        out['native_optimizer']=kernel._optimizer.provenance
    else:kernel=SpatialXYZTransition(model,case['limits'],terms_evaluator=core.contact_terms)
    kernel.prepare()
    try:
        for mode in (('idle','shared') if options.kernel=='native' else ('idle','shared','reserved')):
            workers=[];record=dict(mode=mode,commands=[],ready=[],trials=[],cleanup=[])
            try:
                if mode!='idle':
                    worker_mask=mask if mode=='shared' else others
                    for _ in others:
                        command=[sys.executable,str(task/'cpu-contention-worker.py'),json.dumps(worker_mask)]
                        p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        workers.append(p);record['commands'].append(command)
                    for p in workers:
                        if not select.select([p.stdout],[],[],5.)[0]:raise RuntimeError('load preparation deadline')
                        record['ready'].append(json.loads(p.stdout.readline()))
                    os.sched_setaffinity(0,mask if mode=='shared' else {reserved})
                    for p in workers:p.stdin.write(b'g');p.stdin.flush()
                    time.sleep(.05)
                record['numeric_affinity']=sorted(os.sched_getaffinity(0))
                for i in range(48):
                    before=stats();row=dict(index=i,before=before)
                    try:kernel.step(**case['args']);row['success']=True
                    except ValueError as e:row.update(success=False,error=str(e))
                    after=stats();row.update(after=after,attempt=kernel.last_attempt)
                    row['delta']={k:after[k]-before[k] for k in ('voluntary','involuntary','major_faults','minor_faults','raw_ns','cpu_ns')}
                    row['delta']['runqueue_delay_ns']=after['schedstat'][1]-before['schedstat'][1]
                    record['trials'].append(row)
            finally:
                os.sched_setaffinity(0,mask)
                for p in workers:
                    try:p.stdin.write(b's');p.stdin.flush()
                    except BrokenPipeError:pass
                for p in workers:
                    code=p.wait(timeout=10.);tail=p.stdout.read().decode();error=p.stderr.read().decode()
                    p.stdin.close();p.stdout.close();p.stderr.close()
                    record['cleanup'].append(dict(pid=p.pid,returncode=code,tail=tail,stderr=error,forced=False))
                out['modes'].append(record);path.write_text(json.dumps(out,indent=2))
    finally:kernel.close();os.sched_setaffinity(0,mask)
out['final_affinity']=sorted(os.sched_getaffinity(0));out['method_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
out['background_method_sha256']=hashlib.sha256((task/'cpu-contention-worker.py').read_bytes()).hexdigest()
out['sources']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (nav/'integrated_robot_navigation').glob('*.py')}
path.write_text(json.dumps(out,indent=2))
print(json.dumps(dict(path=str(path),original_affinity=mask,final_affinity=out['final_affinity'],
    modes=[dict(mode=r['mode'],trials=len(r['trials']),failures=sum(not t['success'] for t in r['trials']),
        failures_with_involuntary_switch=sum(not t['success'] and t['delta']['involuntary']>0 for t in r['trials']),
        maximum_runqueue_delay_ns=max(t['delta']['runqueue_delay_ns'] for t in r['trials']),
        maximum_wall_ns=max(list(t['attempt']['stages'].values())[-1]['wall_ns'] for t in r['trials']),
        all_load_children_normal=all(p['returncode']==0 and not p['forced'] for p in r['cleanup'])) for r in out['modes']]),indent=2))
