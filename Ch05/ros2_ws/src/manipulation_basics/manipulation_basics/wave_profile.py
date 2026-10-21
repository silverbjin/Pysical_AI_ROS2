"""Pure mathematical joint motion contract for Ch05 Hello Robot."""

import math

JOINT_NAMES = ('joint1', 'joint2', 'joint3', 'joint4')
READY_POSE = (0.0, -0.5, 0.8, 0.0)
J1_AMPLITUDE, J1_OMEGA = 0.22, 0.8
J4_AMPLITUDE, J4_OMEGA = 0.28, 2.0


def wave_target(elapsed_sec, lookahead_sec=0.15):
    """Return (position, velocity) targets at a modest look-ahead horizon."""
    if (not math.isfinite(elapsed_sec) or not math.isfinite(lookahead_sec)
            or elapsed_sec < 0 or lookahead_sec < 0):
        raise ValueError('time must be finite and nonnegative')
    t = elapsed_sec + lookahead_sec
    positions = (J1_AMPLITUDE * math.sin(J1_OMEGA * t), -0.5, 0.8,
                 J4_AMPLITUDE * math.sin(J4_OMEGA * t))
    velocities = (J1_AMPLITUDE * J1_OMEGA * math.cos(J1_OMEGA * t), 0.0,
                  0.0, J4_AMPLITUDE * J4_OMEGA * math.cos(J4_OMEGA * t))
    return positions, velocities


def pose_reached(joint_positions, tolerance_rad=0.1):
    """Require all named joints to be finite and close to the ready pose."""
    return (len(joint_positions) == 4 and tolerance_rad > 0
            and all(math.isfinite(value) and abs(value - goal) <= tolerance_rad
                    for value, goal in zip(joint_positions, READY_POSE)))
