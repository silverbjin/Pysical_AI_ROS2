"""Issue #181: fail-closed same-PostUpdate contact/geometry classifier.

A positive contact event with a separating axis >1mm is *physically impossible*
for a true 15x30x80mm finger box and conservative rod enclosing BOX.
This classifier does NOT assert root cause inside DART; it distinguishes
source ECS contact component absent, stale component stamp, and impossible
same-frame positive contact. No ROS/Gazebo dependency.
"""
import math

def classify_same_ecs_frame(sim_time_s, finger_rod_obb_gap_m,
                            ecs_data_present, ecs_rod_pair_count,
                            ecs_contact_stamp_s, margin_m=.001):
    if not all(math.isfinite(x) for x in (sim_time_s, finger_rod_obb_gap_m, margin_m)):
        raise ValueError('G04B_INVALID_ECS_GEOMETRY_OR_TIME')
    if sim_time_s < 0 or margin_m <= 0 or type(ecs_data_present) is not bool:
        raise ValueError('G04B_INVALID_ECS_CONTACT_FIELDS')
    if not ecs_data_present:
        return 'CONTACT_ECS_COMPONENT_NOT_PRESENT_UNOBSERVED'
    if not isinstance(ecs_rod_pair_count, int) or ecs_rod_pair_count < 0:
        raise ValueError('G04B_INVALID_ECS_PAIR_COUNT')
    if ecs_rod_pair_count == 0:
        return 'NO_CONTACT_PAIR_ECS'
    if not math.isfinite(ecs_contact_stamp_s):
        return 'ECS_CONTACT_STAMP_MISSING'
    # Contact component may lag the PostUpdate frame; do not blame the
    # solver until same-time evidence excludes this sampling explanation.
    if abs(ecs_contact_stamp_s-sim_time_s)>.025:
        return 'ECS_CONTACT_COMPONENT_STALE_OR_FUTURE'
    if finger_rod_obb_gap_m > margin_m:
        return 'ECS_SAME_FRAME_PHYSICALLY_IMPOSSIBLE_CONTACT'
    return 'GEOMETRY_BOUNDS_OVERLAP_CONTACT_STILL_UNPROVEN'
