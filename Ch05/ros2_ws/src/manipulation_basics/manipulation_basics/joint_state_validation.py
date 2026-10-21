"""ROS-independent validation of sensor_msgs/JointState array semantics."""

import math


def extract_joint_measurement(names, positions, velocities, target):
    """Return (position, optional velocity); None if target data is invalid.

    Missing velocities are unknown, never silently fabricated as zero.
    """
    try:
        index = names.index(target)
    except ValueError:
        return None
    if index >= len(positions):
        return None
    position = positions[index]
    if not math.isfinite(position):
        return None
    velocity = None
    if index < len(velocities) and math.isfinite(velocities[index]):
        velocity = velocities[index]
    return position, velocity
