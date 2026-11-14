#!/usr/bin/env python3
"""G04B #181: collision-geometry-derived symmetric physical grasp goal.

This is NOT a grasp-verdict function. Native Gazebo bilateral contacts, object
world-Z lift, hold and place are separately required after control succeeds.
"""
import math

ORIGINAL_OPEN_FACE_GAP_M=.045
ROD_DIAMETER_M=.024
SYMMETRIC_COMPRESSION_PER_FINGER_M=.0005

def symmetric_close_joint_target(open_face_gap_m=ORIGINAL_OPEN_FACE_GAP_M,
                                 rod_diameter_m=ROD_DIAMETER_M,
                                 compression_per_finger_m=SYMMETRIC_COMPRESSION_PER_FINGER_M):
    values=(open_face_gap_m,rod_diameter_m,compression_per_finger_m)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("G04B_SYMMETRIC_TARGET_NONFINITE")
    if not (0<rod_diameter_m<open_face_gap_m and 0<compression_per_finger_m<=.001):
        raise ValueError("G04B_SYMMETRIC_TARGET_INVALID_GEOMETRY")
    first_contact=(open_face_gap_m-rod_diameter_m)/2
    commanded=first_contact+compression_per_finger_m
    if not 0<commanded<.025:
        raise ValueError("G04B_SYMMETRIC_TARGET_JOINT_LIMIT")
    return commanded
