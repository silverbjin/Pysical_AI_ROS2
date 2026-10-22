"""ROS-independent input validation; all times are seconds in one clock domain."""
import math

LEG_NAMES = tuple(f'{leg}_{joint}_joint' for leg in ('fr', 'fl', 'rr', 'rl')
                  for joint in ('hip', 'thigh', 'calf'))
ARM_NAMES = tuple(f'arm_joint_{index}' for index in range(1, 7))
STAND = (0.0, -0.5, 1.0) * 4
SAFE_ARM = (0.0,) * 6


def joint_snapshot(names, values, required):
    if len(names) != len(values) or len(names) != len(set(names)):
        return None
    data = dict(zip(names, values))
    if not all(name in data and math.isfinite(data[name]) for name in required):
        return None
    return [data[name] for name in required]


def safe_arm(values, receipt_age):
    return (values is not None and len(values) == 6 and 0 <= receipt_age <= 0.5
            and all(math.isfinite(value) and abs(value) < 0.06 for value in values))


def valid_pair(image_stamp, odom_stamp, now):
    return (all(math.isfinite(value) and value > 0 for value in (image_stamp, odom_stamp, now))
            and abs(image_stamp - odom_stamp) <= 0.05
            and 0 <= now - min(image_stamp, odom_stamp) <= 0.3
            and max(image_stamp, odom_stamp) <= now)


def validate_target(name, frame, stamp, now, position, quaternion, dry_run):
    if not dry_run:
        return 'MoveIt and physical grasp are not implemented; set dry_run=true'
    if not name.strip() or len(name) > 128:
        return 'object_name must contain 1..128 characters'
    if frame != 'base_link':
        return 'target frame must be base_link; TF transformation is required upstream'
    if not math.isfinite(stamp) or stamp <= 0 or not -0.05 <= now - stamp <= 0.3:
        return 'target timestamp is stale, future, or invalid'
    if len(position) != 3 or not all(math.isfinite(value) for value in position):
        return 'target position must be finite'
    if len(quaternion) != 4 or not all(math.isfinite(value) for value in quaternion):
        return 'target quaternion must be finite'
    if abs(sum(value * value for value in quaternion) - 1) > 0.01:
        return 'target quaternion must be normalized'
    return ''
