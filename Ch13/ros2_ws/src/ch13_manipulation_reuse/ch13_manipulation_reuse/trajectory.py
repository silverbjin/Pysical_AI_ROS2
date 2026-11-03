"""Bounded C2 joint trajectories, exact polynomial extrema and braking hold."""
import bisect
import math
import numpy as np
from numpy.polynomial import Polynomial

JOINTS=tuple('joint'+str(i) for i in range(1,7))


class Trajectory:
    @classmethod
    def from_points(cls,names,points,current,limits,vmax=.05,amax=.10):
        if len(names)!=6 or set(names)!=set(JOINTS) or len(set(names))!=6:
            raise ValueError('exactly joint1..joint6 required')
        if not 2<=len(points)<=10000:
            raise ValueError('2..10000 trajectory points required')
        order=[names.index(j) for j in JOINTS]
        values=[]
        for point in points:
            t=float(point['time'])
            fields=[]
            for key in ('positions','velocities','accelerations'):
                raw=point.get(key,())
                if key!='positions' and len(raw)==0:raw=[0.]*6
                if len(raw)!=6:raise ValueError('six '+key+' required')
                value=np.asarray(raw,dtype=float)[order].copy()
                if not np.isfinite(value).all():raise ValueError('nonfinite trajectory')
                fields.append(value)
            if not math.isfinite(t) or t<0:raise ValueError('invalid time')
            values.append((t,*fields))
        if values[0][0]!=0. or values[-1][0]>120.:
            raise ValueError('start at time zero; duration at most120sim seconds')
        if np.shape(current)!=(6,) or not np.isfinite(current).all():raise ValueError('invalid measured start')
        if np.max(abs(values[0][1]-current))>.05:raise ValueError('start discontinuity')
        if np.max(abs(values[-1][2]))>1e-8 or np.max(abs(values[-1][3]))>1e-8:
            raise ValueError('terminal velocity and acceleration must be zero')
        result=cls()
        result.limits=np.asarray(limits,dtype=float).copy()
        if (result.limits.shape!=(6,2) or not np.isfinite(result.limits).all()
                or np.any(result.limits[:,0]>=result.limits[:,1])
                or not math.isfinite(vmax) or not math.isfinite(amax) or min(vmax,amax)<=0):
            raise ValueError('invalid trajectory bounds')
        result.vmax,result.amax=float(vmax),float(amax)
        result.times=tuple(p[0] for p in values)
        result.duration=result.times[-1]
        segments=[]
        for first,last in zip(values,values[1:]):
            T=last[0]-first[0]
            if T<.002:raise ValueError('times must increase by at least one physics tick')
            c=np.zeros((6,6));c[0:3]=[first[1],first[2],first[3]/2]
            rhs=np.array([last[1]-c[0]-c[1]*T-c[2]*T*T,
                          last[2]-c[1]-2*c[2]*T,last[3]-2*c[2]])
            c[3:]=np.linalg.solve([[T**3,T**4,T**5],[3*T*T,4*T**3,5*T**4],
                                   [6*T,12*T*T,20*T**3]],rhs)
            for axis in range(6):
                p=Polynomial(c[:,axis])
                for derivative,lo,hi in ((0,*result.limits[axis]),(1,-vmax,vmax),(2,-amax,amax)):
                    poly=p.deriv(derivative)
                    candidates=[0.,T]+[float(r.real) for r in poly.deriv().roots()
                                       if abs(r.imag)<1e-8 and 0<r.real<T]
                    extrema=poly(np.asarray(candidates))
                    if extrema.min()<lo-1e-8 or extrema.max()>hi+1e-8:
                        raise ValueError(('trajectory bound',JOINTS[axis],derivative,float(extrema.min()),float(extrema.max())))
            c.flags.writeable=False
            segments.append(c)
        result.segments=tuple(segments)
        return result

    def sample(self,time_s):
        if not math.isfinite(time_s):raise ValueError('nonfinite trajectory time')
        time_s=max(0.,min(self.duration,float(time_s)))
        index=min(len(self.segments)-1,max(0,bisect.bisect_right(self.times,time_s)-1))
        local=time_s-self.times[index]
        c=self.segments[index]
        return tuple(np.array([Polynomial(c[:,axis]).deriv(d)(local) for axis in range(6)]) for d in (0,1,2))

    def brake(self,time_s):
        q,v,a=self.sample(time_s)
        duration=max(.5,3*float(np.max(abs(v)))/self.amax)
        for _ in range(4):
            # Integrated symmetric deceleration, including the current acceleration.
            target=q+v*duration/2+a*duration*duration/12
            points=[dict(time=0.,positions=q,velocities=v,accelerations=a),
                    dict(time=duration,positions=target)]
            try:return type(self).from_points(JOINTS,points,q,self.limits,self.vmax,self.amax)
            except ValueError:
                duration*=1.5
        raise ValueError('no bounded braking trajectory inside joint limits')
