"""Original closed state, scalar-vs-small-NumPy arithmetic. No engine/ROS init."""
import hashlib,json,math,statistics,sys,time,uuid
from functools import lru_cache
from pathlib import Path
import numpy as np
from integrated_robot_navigation.support import _mass_plan,center_of_mass
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.projection import body_rotation

I=(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.)
def mul(a,b):
    return tuple(a[i]*b[j]+a[i+1]*b[4+j]+a[i+2]*b[8+j]+(a[i+3] if j==3 else 0.)
        for i in (0,4,8) for j in range(4))
def inv(a):
    return (a[0],a[4],a[8],-(a[0]*a[3]+a[4]*a[7]+a[8]*a[11]),
        a[1],a[5],a[9],-(a[1]*a[3]+a[5]*a[7]+a[9]*a[11]),
        a[2],a[6],a[10],-(a[2]*a[3]+a[6]*a[7]+a[10]*a[11]))
@lru_cache(maxsize=32)
def plan(urdf,spec):
    steps,moments,total,owner,fixed,_,_= _mass_plan(urdf,spec)
    return (tuple((name,parent,tuple(origin[:3].flat),kind,tuple(axis),tuple(skew.flat),tuple(squared.flat),bounds)
        for name,parent,origin,kind,axis,skew,squared,bounds in steps),
        tuple((key,tuple(value)) for key,value in moments),total,owner,tuple(fixed[:3].flat))
def scalar(model,joints,body_pose):
    pose=np.asarray(body_pose,dtype=float)
    if (pose.shape!=(4,4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3],(0.,0.,0.,1.),atol=1e-10)
            or not np.allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-8)
            or not math.isclose(np.linalg.det(pose[:3,:3]),1.,abs_tol=1e-8)):
        raise ValueError('rigid body pose required')
    spec=tuple((link,mass,point if isinstance(point,tuple) else tuple(point)) for link,(mass,point) in model.masses.items())
    steps,moments,total,base_owner,base_fixed=plan(model.urdf,spec)
    frames={None:I}
    for name,parent,origin,kind,axis,skew,squared,bounds in steps:
        if name not in joints:raise ValueError('missing named joint position')
        value=joints[name]
        if not math.isfinite(value) or bounds is not None and not bounds[0]<=value<=bounds[1]:
            raise ValueError('joint position outside finite limits')
        if kind=='prismatic':change=(1.,0.,0.,axis[0]*value,0.,1.,0.,axis[1]*value,0.,0.,1.,axis[2]*value)
        else:
            s,c=math.sin(value),1-math.cos(value)
            r=tuple(float(i in (0,4,8))+s*skew[i]+c*squared[i] for i in range(9))
            change=(*r[:3],0.,*r[3:6],0.,*r[6:],0.)
        frames[name]=mul(mul(frames[parent],origin),change)
    inverse=inv(mul(frames[base_owner],base_fixed))
    m=[0.,0.,0.,0.]
    for owner,point in moments:
        transform=frames[owner]
        for row in range(3):
            i=row*4;m[row]+=sum(transform[i+j]*point[j] for j in range(4))
        m[3]+=point[3]
    world=mul(tuple(pose[:3].flat),inverse)
    return tuple(sum(world[i+j]*m[j] for j in range(4))/total for i in (0,4,8))

root=Path(sys.argv[1]);t=json.loads((root/'teardown.json').read_text());assert t['parent_reaped'] and not t['residual_live_pids']
c=json.loads((root/'controller_report.json').read_text());result=json.loads((root/'result.json').read_text())
model=compile_model(Path(result['scene']['robot']['path']).read_text());assert model.model_sha256==c['model_sha256']
samples=c['first_fault']['samples'];q=samples['joints']['data']['position'];pose=np.eye(4)
pose[:3,:3]=body_rotation(samples['body']['data'])[0];pose[:3,3]=samples['body']['data']['position']
errors=[];rng=np.random.default_rng(130528)
for _ in range(100):
    values={name:float(rng.uniform(bounds[0],bounds[1])) for name,bounds in model.limits.items()}
    p=pose.copy();p[:3,3]=rng.uniform(-10.,10.,size=3)
    errors.append(float(np.max(np.abs(np.asarray(scalar(model,values,p))-center_of_mass(model,values,p)))))
assert max(errors)<2e-12
costs={'numpy':dict(wall=[],cpu=[]),'scalar':dict(wall=[],cpu=[])}
for _ in range(500):
    for name,callback in (('numpy',center_of_mass),('scalar',scalar)):
        wall=time.perf_counter_ns();cpu=time.thread_time_ns();callback(model,q,pose)
        costs[name]['cpu'].append(time.thread_time_ns()-cpu);costs[name]['wall'].append(time.perf_counter_ns()-wall)
def stats(xs):return dict(mean_ns=statistics.mean(xs),median_ns=statistics.median(xs),max_ns=max(xs))
report=dict(scope=__doc__,trial=root.name,model_sha256=model.model_sha256,
    original_report_sha256=hashlib.sha256((root/'controller_report.json').read_bytes()).hexdigest(),
    maximum_absolute_error_m=max(errors),states=100,calls_each=500,
    costs={name:{kind:stats(values) for kind,values in kinds.items()} for name,kinds in costs.items()},
    no_acceptance_claim=True)
out=Path(sys.argv[2])/('scalar-mass-prototype-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes());(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(output=str(out),**report)))
