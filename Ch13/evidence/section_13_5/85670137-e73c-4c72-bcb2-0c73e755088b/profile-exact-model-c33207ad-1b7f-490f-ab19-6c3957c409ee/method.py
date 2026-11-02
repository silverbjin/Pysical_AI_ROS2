"""One-thread postmortem math profile at actual failure; exact run limits."""
import cProfile,hashlib,json,os,pstats,statistics,sys,time,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.samples import Sample,SensorBundle
repo=Path(__file__).resolve().parents[3]
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/'native-g2-mujoco-4163d57d-801c-40e3-96b7-94a1e3561da7'
closed=json.loads((root/'teardown.json').read_text());assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text());fault=report['first_fault']
result=json.loads((root/'result.json').read_text());profile=json.loads((root/'validated_profile.json').read_text())
target=base/('profile-exact-model-'+str(uuid.uuid4()));target.mkdir()
model=compile_model(Path(result['scene']['robot']['path']).read_text())
bundle=SensorBundle(**{name:Sample(**value) for name,value in fault['samples'].items()})
machine=CrawlMachine(model,profile['limits']);ros=fault['ros_ns'];wall=fault['wall_ns']
machine.reset(bundle,ros,wall);assert machine.state!='FAULT',machine.reason
machine.reference_body=np.asarray(report['current']['reference_body'])
machine._targets={key:np.asarray(value) for key,value in report['current']['targets'].items()}
machine.state='CRAWL';machine.phase='SHIFT';q=bundle.joints.data['position']
callbacks=dict(measure=lambda:machine._measure(bundle,ros,wall),solve=lambda:machine._solve(q,True))
stats={};profiler=cProfile.Profile()
for name,callback in callbacks.items():
    cpu=[];elapsed=[]
    for _ in range(200):
        a=time.thread_time_ns();b=time.monotonic_ns();callback()
        elapsed.append(time.monotonic_ns()-b);cpu.append(time.thread_time_ns()-a)
    stats[name]=dict(mean_cpu_ns=statistics.mean(cpu),mean_wall_ns=statistics.mean(elapsed),max_cpu_ns=max(cpu))
    profiler.enable()
    for _ in range(100):callback()
    profiler.disable()
profiler.dump_stats(target/'math.prof')
with (target/'functions.txt').open('x') as stream:pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(22)
data=dict(scope='postmortem_same_state_math_not_live_native_stack',trial=root.name,
    limits_sha256=hashlib.sha256((root/'validated_profile.json').read_bytes()).hexdigest(),
    report_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),stats=stats)
(target/'result.json').write_text(json.dumps(data,indent=2));(target/'method.py').write_bytes(Path(__file__).read_bytes())
print(target,flush=True);print(json.dumps(data),flush=True);print((target/'functions.txt').read_text(),flush=True)
