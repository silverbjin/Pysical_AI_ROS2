"""Bounded C2 joint trajectories, exact polynomial extrema and braking hold."""
import bisect
import math
import time
import numpy as np
from numpy.polynomial import Polynomial

JOINTS=tuple('joint'+str(i) for i in range(1,7))
BERNSTEIN=np.array([[math.comb(i,k)/math.comb(5,k) if k<=i else 0. for k in range(6)] for i in range(6)])


class Trajectory:
    @classmethod
    def from_points(cls,names,points,current,limits,vmax=.05,amax=.10,validation_deadline=None):
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
        # Batch the common proof in NumPy. Hundreds of per-axis Python loops
        # otherwise compete with the physics/RX threads for the same GIL.
        T=np.diff(result.times)
        if np.any(T<.002):raise ValueError('times must increase by at least one physics tick')
        first=np.asarray([p[1:] for p in values[:-1]])
        last=np.asarray([p[1:] for p in values[1:]])
        tau=T[:,None];coefficients=np.zeros((len(T),6,6))
        coefficients[:,:3,:]=first;coefficients[:,2,:]/=2
        delta=last[:,0]-coefficients[:,0]-coefficients[:,1]*tau-coefficients[:,2]*tau*tau
        velocity=last[:,1]-coefficients[:,1]-2*coefficients[:,2]*tau
        acceleration=last[:,2]-2*coefficients[:,2]
        coefficients[:,3]=(10*delta-4*velocity*tau+.5*acceleration*tau*tau)/tau**3
        coefficients[:,4]=(-15*delta+7*velocity*tau-acceleration*tau*tau)/tau**4
        coefficients[:,5]=(6*delta-3*velocity*tau+.5*acceleration*tau*tau)/tau**5
        if not np.isfinite(coefficients).all():raise ValueError('nonfinite trajectory coefficients')
        scaled=coefficients*T[:,None,None]**np.arange(6)[None,:,None]
        hull=BERNSTEIN@scaled
        velocity_hull=5*np.diff(hull,axis=1)/T[:,None,None]
        acceleration_hull=4*np.diff(velocity_hull,axis=1)/T[:,None,None]
        bounds=((result.limits[:,0],result.limits[:,1]),(-vmax,vmax),(-amax,amax))
        for derivative,cloud in enumerate((hull,velocity_hull,acceleration_hull)):
            lo,hi=bounds[derivative]
            uncertain=(cloud.min(axis=1)<lo-1e-8)|(cloud.max(axis=1)>hi+1e-8)
            for index,axis in np.argwhere(uncertain):
                if validation_deadline is not None and time.monotonic()>validation_deadline:
                    raise ValueError('trajectory validation deadline')
                duration=T[index];poly=Polynomial(coefficients[index,:,axis]).deriv(derivative)
                candidates=[0.,duration]+[float(r.real) for r in poly.deriv().roots()
                                         if abs(r.imag)<1e-8 and 0<r.real<duration]
                extrema=poly(np.asarray(candidates));lower=np.broadcast_to(lo,(6,))[axis];upper=np.broadcast_to(hi,(6,))[axis]
                if extrema.min()<lower-1e-8 or extrema.max()>upper+1e-8:
                    raise ValueError(('trajectory bound',JOINTS[axis],derivative,float(extrema.min()),float(extrema.max())))
        if validation_deadline is not None and time.monotonic()>validation_deadline:
            raise ValueError('trajectory validation deadline')
        segments=[]
        for c in coefficients:
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
        q=c[0]+local*(c[1]+local*(c[2]+local*(c[3]+local*(c[4]+local*c[5]))))
        v=c[1]+local*(2*c[2]+local*(3*c[3]+local*(4*c[4]+local*5*c[5])))
        a=2*c[2]+local*(6*c[3]+local*(12*c[4]+local*20*c[5]))
        return q,v,a

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
