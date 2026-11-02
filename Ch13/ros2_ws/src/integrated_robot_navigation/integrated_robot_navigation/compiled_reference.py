"""Compile immutable URDF leg geometry, evaluate every CURRENT grid point.

Same Rx/Ry/Ry branch search, exact FK residual and capsule/box distance as the
independent public IK/clearance functions. No measured pose/result is cached.
The 28 nominal/future samples and all physical/gait bounds remain unchanged.
"""
from dataclasses import dataclass
import math
import numpy as np
from .carry_profile import _validate_limits
from .leg_kinematics import _leg_spec,_thigh_box_spec,_segment_box_distance


@dataclass(frozen=True,slots=True)
class _Leg:
    hip: tuple
    offset: float
    upper: float
    lower: float
    names: tuple
    physical: tuple
    allowed: tuple
    half: tuple
    inverse: tuple
    radius: float

    def forward(self,q):
        roll,thigh,knee=q
        x=-self.upper*math.sin(thigh)-self.lower*math.sin(thigh+knee)
        z=-self.upper*math.cos(thigh)-self.lower*math.cos(thigh+knee)
        c,s=math.cos(roll),math.sin(roll)
        return (self.hip[0]+x,self.hip[1]+self.offset*c-z*s,self.hip[2]+self.offset*s+z*c)

    def ik(self,target,previous):
        x,y,z=(v-h for v,h in zip(target,self.hip));radial=y*y+z*z-self.offset*self.offset
        if radial<=0. or not math.isfinite(radial):raise ValueError('unreachable hip offset')
        best=None;score=math.inf
        for local_z in (-math.sqrt(radial),math.sqrt(radial)):
            roll=math.atan2(z,y)-math.atan2(local_z,self.offset)
            roll=math.atan2(math.sin(roll),math.cos(roll))
            cosine=(x*x+local_z*local_z-self.upper*self.upper-self.lower*self.lower)/(2*self.upper*self.lower)
            if not math.isfinite(cosine) or cosine < -1.-1e-12 or cosine > 1.+1e-12:continue
            knee_abs=math.acos(min(1.,max(-1.,cosine)))
            for knee in (knee_abs,-knee_abs):
                thigh=math.atan2(-x,-local_z)-math.atan2(self.lower*math.sin(knee),self.upper+self.lower*math.cos(knee))
                lo,hi=self.physical[1]
                for turn in range(math.ceil((lo-thigh)/math.tau),math.floor((hi-thigh)/math.tau)+1):
                    q=(roll,thigh+turn*math.tau,knee)
                    if all(a<=v<=b for v,(a,b) in zip(q,self.physical)):
                        actual=self.forward(q)
                        if sum((a-b)**2 for a,b in zip(actual,target))<1e-16:
                            distance=sum((a-b)**2 for a,b in zip(q,previous))
                            if distance<score:best,score=q,distance
        if best is None:raise ValueError('unreachable target or joint limit')
        return best

    def clearance(self,q):
        roll,thigh,_=q;c,s=math.cos(roll),math.sin(roll)
        start=(self.hip[0],self.hip[1]+self.offset*c,self.hip[2]+self.offset*s)
        end=(start[0]-self.upper*math.sin(thigh),start[1]+self.upper*math.cos(thigh)*s,
            start[2]-self.upper*math.cos(thigh)*c)
        def transform(p):
            x,y,z=p
            return tuple(row[0]*x+row[1]*y+row[2]*z+row[3] for row in self.inverse[:3])
        return _segment_box_distance(transform(start),transform(end),self.half)-self.radius


class CompiledReferenceEnvelope:
    def __init__(self,model,limits):
        _validate_limits(limits)
        self.model_sha256=model.model_sha256;self.feet=tuple(model.feet)
        self._joint_bounds={n:tuple(v[:2]) for n,v in model.limits.items()};self._legs={}
        for f in self.feet:
            hip,offset,upper,lower,names=_leg_spec(model.urdf,f)
            half,inverse,radius=_thigh_box_spec(model.urdf,f)
            physical=tuple(self._joint_bounds[n] for n in names)
            allowed=tuple((max(limits['gait_joint_bounds'][p][0],a),
                min(limits['gait_joint_bounds'][p][1],b)) for p,(a,b) in zip(('hip','thigh','calf'),physical))
            if any(a>b for a,b in allowed):raise ValueError('empty compiled joint bounds')
            self._legs[f]=_Leg(tuple(float(v) for v in hip),offset,upper,lower,names,physical,allowed,half,inverse,radius)

    def evaluate(self,*,joints,body,targets,envelope,selected,future_targets):
        if (selected not in self.feet or set(joints)!=set(self._joint_bounds)
                or any(set(v)!=set(self.feet) for v in (targets,envelope,future_targets))
                or any(not math.isfinite(joints[n]) or not a<=joints[n]<=b
                    for n,(a,b) in self._joint_bounds.items())):
            raise ValueError('invalid current compiled reference input')
        pose=np.asarray(body,dtype=float)
        if pose.shape!=(4,4) or not np.isfinite(pose).all() or not np.allclose(pose[3],[0.,0.,0.,1.],atol=1e-12):
            raise ValueError('finite affine reference body required')
        try:inverse=tuple(tuple(float(v) for v in row) for row in np.linalg.inv(pose))
        except np.linalg.LinAlgError as error:raise ValueError('singular reference body') from error
        def local(p):
            x,y,z=p
            return tuple(row[0]*x+row[1]*y+row[2]*z+row[3] for row in inverse[:3])
        q=dict(joints);clear=[];bounds=[]
        for f in self.feet:
            position=tuple(float(v) for v in targets[f]);future=tuple(float(v) for v in future_targets[f])
            lo,hi=envelope[f]
            if (len(position)!=3 or len(future)!=3 or not all(math.isfinite(v) for v in (*position,*future,lo,hi)) or lo>hi):
                raise ValueError('finite compiled reference geometry required')
            leg=self._legs[f];seed=tuple(joints[n] for n in leg.names)
            nominal=leg.ik(local(position),seed);q.update(zip(leg.names,nominal));angles=[nominal]
            for u in ((0.,.25,.5,.75,1.) if f==selected else (0.,)):
                x=position[0]*(1.-u)+future[0]*u;y=position[1]*(1.-u)+future[1]*u
                for z in (lo,(lo+hi)/2.,hi):angles.append(leg.ik(local((x,y,z)),seed))
            clear.append(min(leg.clearance(a)-.0001 for a in angles))
            for i,(lo,hi) in enumerate(leg.allowed):
                bounds.extend((min(a[i]-lo for a in angles),min(hi-a[i] for a in angles)))
        return q,np.asarray(clear),np.asarray(bounds)
