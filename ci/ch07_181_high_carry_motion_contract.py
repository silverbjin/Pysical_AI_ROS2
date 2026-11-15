"""Issue #181: single high-carry velocity experiment, physics unchanged.

Original PGS #43690734272 has >25 mm real native custody drift during
high yaw/lateral transport despite good actual arm tracking. Halve only
the transport-high MoveGroup velocity scaling to isolate inertial slip.
"""
BASE_VELOCITY_SCALING = .17
HIGH_VELOCITY_SCALING = BASE_VELOCITY_SCALING / 2
ARM_ACCELERATION_SCALING = .17

def velocity_scaling_for_arm_goal(label):
    if not isinstance(label, str) or not label.strip():
        raise ValueError('G04B_181_INVALID_ARM_STAGE')
    return HIGH_VELOCITY_SCALING if label == 'transfer_high_above_bin' else BASE_VELOCITY_SCALING
