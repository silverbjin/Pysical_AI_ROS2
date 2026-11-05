"""Bounded filled-rectangle route checks against the original static occupancy."""
import numpy as np
from .approach_geometry import footprint_clear


def path_footprint_clear(poses,grid,footprint):
    try:
        if not 1<=len(poses)<=2048:return False
        points=np.asarray(poses,dtype=float);fp=np.asarray(footprint,dtype=float)
        if points.shape!=(len(poses),3) or fp.shape!=(4,2):return False
        if not np.isfinite(points).all() or not np.isfinite(fp).all():return False
        padded=fp+np.sign(fp)*.01  # Same pinned rectangle and Nav2 padding.
        return all(footprint_clear(p,grid,padded) for p in points)
    except (KeyError,IndexError,TypeError,ValueError,OverflowError):return False
