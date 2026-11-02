"""Frozen Ch13 NumPy oracle before scalar allocation reduction.

Own source: leg_kinematics.py at local HEAD4e87f6f plus the recorded Task8
worktree, full source SHA256 ed40a33c00029829bfcf3b4175680ea37bdd3dfe04fa1fced65f304acc8bfe01.
No external code. Preserve this expression independently of the new kernel.
"""
import math
import numpy as np


def numpy_segment_box_distance(start,end,half):
    start,end,half=(np.asarray(value,dtype=float) for value in (start,end,half))
    delta=end-start
    boundaries=[0.,1.]
    for axis in range(3):
        if delta[axis]!=0:
            for edge in (-half[axis],half[axis]):
                t=float((edge-start[axis])/delta[axis])
                if 0.<t<1.:boundaries.append(t)
    boundaries=sorted(boundaries);best=math.inf
    for lo,hi in zip(boundaries,boundaries[1:]):
        middle=start+delta*((lo+hi)/2)
        active=np.abs(middle)>half
        slope=delta[active];origin=start[active]-np.sign(middle[active])*half[active]
        norm=float(slope@slope)
        t=min(hi,max(lo,-float(origin@slope)/norm)) if norm else lo
        gap=np.maximum(np.abs(start+delta*t)-half,0.)
        best=min(best,float(gap@gap))
    return math.sqrt(best)
