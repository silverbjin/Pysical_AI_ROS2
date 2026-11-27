"""Table-only radial compensation; isolated V3 remains immutable."""
import math
from arc_straight_profile import (ANGLE,ARC_STOP_LEAD,ARC_V_FEED,ARC_V_MAX,
                                  ARC_W,ARC_W_MAX,ARC_CROSS_W_GAIN,arc_error,clip)
TABLE_CROSS_V_GAIN=.45

def table_arc_command(p):
    if not all(math.isfinite(x) for x in p):return None
    err,along,cross=arc_error(p)
    if -p[2]<-.08 or err>.05:return None
    if -p[2]>=ANGLE-ARC_STOP_LEAD:return (0.,0.)
    return (clip(ARC_V_FEED+.6*along+TABLE_CROSS_V_GAIN*cross,0,ARC_V_MAX),
            clip(ARC_W+ARC_CROSS_W_GAIN*cross,ARC_W,ARC_W_MAX))
