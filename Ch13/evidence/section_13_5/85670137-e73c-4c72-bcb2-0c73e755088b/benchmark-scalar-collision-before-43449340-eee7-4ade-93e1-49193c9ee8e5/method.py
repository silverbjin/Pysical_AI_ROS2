"""Same recorded q and URDF geometry, no engine or acceptance promotion."""
import hashlib,json,math,statistics,sys,time,uuid
from pathlib import Path
import numpy as np
repo=Path.cwd();nav=repo/'Ch13/ros2_ws/src/integrated_robot_navigation'
sys.path[:0]=[str(nav),str(nav/'test')]
from integrated_robot_navigation import leg_kinematics as legs
from integrated_robot_navigation.model import compile_model
from segment_box_reference import numpy_segment_box_distance
root=Path(sys.argv[1]);label=sys.argv[2]
closed=json.loads((root/'teardown.json').read_text())
assert closed['parent_reaped'] and not closed['residual_live_pids']
report=json.loads((root/'controller_report.json').read_text());result=json.loads((root/'result.json').read_text())
model=compile_model(Path(result['scene']['robot']['path']).read_text())
q=report['first_fault']['samples']['joints']['data']['position']
angles={f:tuple(q[f[:2]+'_'+p+'_joint'] for p in ('hip','thigh','calf')) for f in model.feet}
# Copy only immutable geometry OUTSIDE timing, exactly as the previous bounded
# URDF cache did. Both candidates validate/use the CURRENT q for every call.
geometry={f:tuple((np.asarray(a) if i<2 else a) for i,a in enumerate(legs._thigh_box_spec(model.urdf,f))) for f in model.feet}
def legacy(foot):
    value=angles[foot];legs.fk_leg(model,foot,value)
    hip,offset,upper,_,_=legs._leg_spec(model.urdf,foot)
    half,inverse,radius=geometry[foot]
    roll,thigh,_=value;c,s=math.cos(roll),math.sin(roll)
    start=hip+np.array([0.,offset*c,offset*s])
    end=start+np.array([-upper*math.sin(thigh),upper*math.cos(thigh)*s,-upper*math.cos(thigh)*c])
    start=(inverse@np.r_[start,1.])[:3];end=(inverse@np.r_[end,1.])[:3]
    return numpy_segment_box_distance(start,end,half)-radius
def current(foot):return legs.thigh_trunk_clearance(model,foot,angles[foot])
expected={f:legacy(f) for f in model.feet}
for f in model.feet:assert abs(current(f)-expected[f])<=1e-13
timings={}
for name,fn in (('frozen_numpy',legacy),('current',current)):
    spans=[]
    for _ in range(5):
        begin=time.thread_time_ns()
        for _ in range(200):
            for f in model.feet:fn(f)
        spans.append((time.thread_time_ns()-begin)/800)
    timings[name]=dict(cpu_ns_per_clearance=spans,median=statistics.median(spans))
speedup=timings['frozen_numpy']['median']/timings['current']['median']
out=root.parent/('benchmark-scalar-collision-'+label+'-'+str(uuid.uuid4()));out.mkdir()
value=dict(scope='offline_same_q_cpu_characterization_not_native_success',trial=root.name,
    model_sha256=model.model_sha256,source_sha256=hashlib.sha256(Path(legs.__file__).read_bytes()).hexdigest(),
    timings=timings,speedup=speedup,required_speedup=2.,passed=speedup>=2.)
(out/'result.json').write_text(json.dumps(value,indent=2));(out/'method.py').write_bytes(Path(__file__).read_bytes())
(out/'segment_box_reference.py').write_bytes((nav/'test/segment_box_reference.py').read_bytes())
print(json.dumps(dict(path=str(out),**value)))
raise SystemExit(0 if value['passed'] else 1)
