"""Issue #181: distinguish live WorldPose from inferred relative-chain pose.
The component may be missing, and a mismatch is not by itself a physics
defect; never promote a fake native geometry receipt.
"""
import math

def classify_pose_provenance(scene_to_helper_m, scene_to_world_component_m,
                             world_component_present, threshold_m=.005):
    if (type(world_component_present) is not bool or
        not math.isfinite(scene_to_helper_m) or scene_to_helper_m < 0 or
        not math.isfinite(threshold_m) or threshold_m <= 0):
        raise ValueError('G04B_INVALID_POSE_SOURCE')
    if not world_component_present:
        return 'WORLD_POSE_COMPONENT_ABSENT_UNDETERMINED'
    if not math.isfinite(scene_to_world_component_m) or scene_to_world_component_m < 0:
        raise ValueError('G04B_INVALID_WORLDPOSE_COMPONENT')
    if scene_to_helper_m > threshold_m and scene_to_world_component_m <= threshold_m:
        return 'HELPER_RELATIVE_CHAIN_DIFFERS_FROM_LIVE_WORLDPOSE'
    if scene_to_helper_m <= threshold_m and scene_to_world_component_m > threshold_m:
        return 'WORLDPOSE_COMPONENT_DIFFERS_FROM_HELPER_AND_SCENE'
    if scene_to_helper_m > threshold_m and scene_to_world_component_m > threshold_m:
        return 'BOTH_DIFFER_FROM_SCENE_SOURCE_UNDETERMINED'
    return 'POSE_SOURCES_CONSISTENT_WITHIN_SCOPE'
