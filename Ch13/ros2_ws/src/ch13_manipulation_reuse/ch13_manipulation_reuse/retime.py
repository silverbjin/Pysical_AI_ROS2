"""Preserve MoveIt waypoints; conservatively time-scale to audited C2 hold."""
import copy
import numpy as np
from .trajectory import Trajectory


def normalize_points(names,points,current,limits,*,refine_scale=False):
    last_error=None
    intervals=np.diff([p['time'] for p in points])
    if len(intervals)==0 or not np.isfinite(intervals).all() or np.any(intervals<=0):
        raise ValueError('nonadvancing MoveIt path time')
    # Scale only to satisfy continuous position/velocity/acceleration bounds.
    # Knot spacing is independent of the physics sampling period.
    def scaled(scale):
        result=copy.deepcopy(points)
        for point in result:
            point['time']*=scale
            point['velocities']=(np.asarray(point.get('velocities',[0.]*6))/scale).tolist()
            point['accelerations']=(np.asarray(point.get('accelerations',[0.]*6))/scale**2).tolist()
        for point in (result[0],result[-1]):
            point['velocities']=[0.]*6;point['accelerations']=[0.]*6
        return result
    lower=1.
    for scale in (1.,1.25,1.5,2.,3.):
        result=scaled(scale)
        try:
            Trajectory.from_points(tuple(names),result,current,limits)
        except ValueError as error:
            last_error=error;lower=scale
            continue
        if refine_scale and scale>1.:
            # Uniform time scaling preserves the entire joint-space curve.
            # Search only inside a proven feasible coarse bracket, then leave
            # 1% margin and prove all original continuous bounds again.
            upper=scale
            for _ in range(12):
                middle=(lower+upper)/2
                try:Trajectory.from_points(tuple(names),scaled(middle),current,limits)
                except ValueError:lower=middle
                else:upper=middle
            scale=min(scale,upper*1.01);result=scaled(scale)
            Trajectory.from_points(tuple(names),result,current,limits)
        return result,scale
    raise ValueError('MoveIt path cannot satisfy the audited trajectory contract: '+str(last_error))
