"""Issue #181: position-only world-pose feedback for physically carried rod."""
import math
BIN_XY=(.55,.25)
LIFT_WRIST=(.48,0.,1.96)
LOWER_WRIST_Z=1.72
BIN_TOP_Z=1.73
ROD_HEIGHT=.08

def corrected_high_target(held_xyz):
    if len(held_xyz)!=3 or not all(math.isfinite(x) for x in held_xyz):
        raise ValueError("G04B_INVALID_HELD_WORLD_POSE")
    if held_xyz[2]<1.98:raise ValueError("G04B_ROD_NOT_HELD_HIGH")
    dx,dy=BIN_XY[0]-held_xyz[0],BIN_XY[1]-held_xyz[1]
    if math.hypot(dx,dy)>.35:raise ValueError("G04B_UNBOUNDED_TRANSFER")
    return [LIFT_WRIST[0]+dx,LIFT_WRIST[1]+dy,LIFT_WRIST[2]]

def custody_offset(rod,finger_center):
    if len(rod)!=3 or len(finger_center)!=3 or not all(
        math.isfinite(x) for x in (*rod,*finger_center)):
        raise ValueError("G04B_INVALID_CUSTODY_FEEDBACK")
    return tuple(rod[i]-finger_center[i] for i in range(3))

def custody_drift(rod,finger_center,held_offset):
    return math.dist(custody_offset(rod,finger_center),held_offset)

def high_arrival_valid(rod,drift):
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.07
            and rod[2]>=1.98 and math.isfinite(drift) and drift<=.04)

def pre_release_valid(rod,drift):
    # Actual bin top is 1.73m, real rod is 80mm tall (centre offset 40mm).
    return (math.hypot(rod[0]-.55,rod[1]-.25)<=.06
            and 1.78<=rod[2]<=1.92
            and math.isfinite(drift) and drift<=.04)
