"""Post-reap synthetic SHIFT using recorded measurements; never native proof."""
import cProfile,copy,hashlib,json,os,pstats,statistics,sys,time,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.samples import Sample,SensorBundle

root=Path(sys.argv[1]).resolve()
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text())
fault=report['first_fault'];result=json.loads((root/'result.json').read_text())
profile=json.loads((root/'validated_profile.json').read_text())
model=compile_model(Path(result['scene']['robot']['path']).read_text())
bundle=SensorBundle(**{key:Sample(**value) for key,value in fault['samples'].items()})
ros,wall=fault['ros_ns'],fault['wall_ns']
machine=CrawlMachine(model,profile['limits'],reference_time_policy='applied_shift_elapsed')
machine.reset(bundle,ros,wall);assert machine.state!='FAULT',machine.reason
machine.state='CRAWL';machine.phase='SHIFT';machine._shift_plan=None
machine._phase_start=ros-1_000_000_000;machine._shift_duration=2.625
machine._offset_start=machine._offset_goal=np.zeros(2)
machine._shift_settled_start=machine._unload_start=None
machine._unloaded_since=None
machine._last_ros=ros-20_000_000;machine._last_wall=wall-20_000_000
machine.reference_body=np.asarray(fault['reference_body'])
machine.travel=machine.reference_body.copy()
machine._targets={key:np.asarray(value) for key,value in fault['targets'].items()}
profiler=cProfile.Profile();spans=[];cpu=[];states={}
for index in range(200):
    item=copy.deepcopy(machine)  # preparation excluded from the kernel timing
    if index>=100:profiler.enable()
    a=time.monotonic_ns();b=time.thread_time_ns()
    output=item.advance(bundle,(.01,0.,0.),ros,wall,reference_permitted=True)
    cpu.append(time.thread_time_ns()-b);spans.append(time.monotonic_ns()-a)
    if index>=100:profiler.disable()
    assert output.state=='CRAWL',output.reason
    assert output.joint_targets and len(output.joint_targets)==12
    states[output.state]=states.get(output.state,0)+1
out=root.parent/('profile-shift-advance-'+str(uuid.uuid4()));out.mkdir()
profiler.dump_stats(out/'kernel.prof')
with (out/'functions.txt').open('x') as stream:
    pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(30)
data=dict(scope='synthetic_full_advance_recorded_measurements_not_exact_live_state_or_acceptance',
    trial=root.name,report_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    uid=os.getuid(),iterations=200,states=states,
    unprofiled_cpu_median_ns=statistics.median(cpu[:100]),
    unprofiled_wall_median_ns=statistics.median(spans[:100]))
(out/'result.json').write_text(json.dumps(data,indent=2))
(out/'method.py').write_bytes(Path(__file__).read_bytes())
print(out);print(json.dumps(data));print((out/'functions.txt').read_text())
