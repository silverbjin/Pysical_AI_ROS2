"""Preserve MoveIt waypoints; conservatively time-scale to audited C2 hold."""
import copy
import numpy as np
from .trajectory import Trajectory


def normalize_points(names,points,current,limits):
    last_error=None
    intervals=np.diff([p['time'] for p in points])
    if len(intervals)==0 or not np.isfinite(intervals).all() or np.any(intervals<=0):
        raise ValueError('nonadvancing MoveIt path time')
    # TOTG can append a valid geometric endpoint less than one physics tick
    # after the preceding waypoint. Stretch the entire path uniformly, with
    # nanosecond rounding headroom, instead of dropping either endpoint.
    tick_scale=max(1.,.002000002/float(intervals.min()))
    for multiplier in (1.,1.25,1.5,2.,3.):
        scale=tick_scale*multiplier
        result=copy.deepcopy(points)
        for point in result:
            point['time']*=scale
            point['velocities']=(np.asarray(point.get('velocities',[0.]*6))/scale).tolist()
            point['accelerations']=(np.asarray(point.get('accelerations',[0.]*6))/scale**2).tolist()
        for point in (result[0],result[-1]):
            point['velocities']=[0.]*6;point['accelerations']=[0.]*6
        try:
            Trajectory.from_points(tuple(names),result,current,limits)
            return result,scale
        except ValueError as error:last_error=error
    raise ValueError('MoveIt path cannot satisfy the audited trajectory contract: '+str(last_error))
