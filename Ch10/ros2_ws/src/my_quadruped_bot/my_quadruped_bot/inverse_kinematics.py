"""Analytical three-DoF leg IK using joint frames from Ch10 URDF/Xacro.

Local target frame: hip roll joint, X forward, Y left, Z up (metres).
The thigh joint origin is offset sideways by +/-0.05 m from the hip roll joint.
The thigh and calf pitch joints have fixed rpy offsets +1.2/-2.4 radians.
"""
import math
import numpy as np


class InverseKinematics:
    def __init__(self, leg_config=None):
        config = leg_config or {}
        self.l1 = float(config.get('hip_side_offset', 0.05))
        self.l2 = float(config.get('thigh_length', 0.25))
        self.l3 = float(config.get('calf_length', 0.25))
        self.thigh_origin_pitch = float(config.get('thigh_origin_pitch', 1.2))
        self.calf_origin_pitch = float(config.get('calf_origin_pitch', -2.4))
        self.hip_limit = (-0.8, 0.8)
        self.thigh_limit = (-1.0, 4.0)
        self.calf_limit = (-2.8, 2.8)
        self.epsilon = 1e-9

    def forward(self, angles, is_right_leg=False):
        """Return foot position in hip-roll joint frame for this simplified URDF chain."""
        q1, q2, q3 = map(float, angles)
        side = -1.0 if is_right_leg else 1.0
        a = self.thigh_origin_pitch + q2
        b = self.calf_origin_pitch + q3
        x = -self.l2 * math.sin(a) - self.l3 * math.sin(a + b)
        z_local = -self.l2 * math.cos(a) - self.l3 * math.cos(a + b)
        y_local = side * self.l1
        y = y_local * math.cos(q1) - z_local * math.sin(q1)
        z = y_local * math.sin(q1) + z_local * math.cos(q1)
        return np.array([x, y, z], dtype=float)

    def solve(self, x, y, z, is_right_leg=False):
        """Return joint angles, or None on unreachable/limit/nonfinite input.

        No target projection: callers can detect unsafe commands explicitly.
        """
        p = np.asarray([x, y, z], dtype=float)
        if not np.all(np.isfinite(p)):
            return None
        x, y, z = map(float, p)
        offset = (-self.l1 if is_right_leg else self.l1)
        rho = math.hypot(y, z)
        if rho < abs(offset) + self.epsilon:
            return None
        q1 = math.atan2(y, -z) - math.asin(max(-1.0, min(1.0, offset / rho)))
        # Below the hip: reject the alternative hip-roll branch above the body.
        z_prime = -math.sqrt(max(0.0, rho * rho - offset * offset))
        distance = math.hypot(x, z_prime)
        if not (abs(self.l2 - self.l3) + self.epsilon <= distance <= self.l2 + self.l3 - self.epsilon):
            return None
        cosine = (distance**2 - self.l2**2 - self.l3**2) / (2.0 * self.l2 * self.l3)
        bend = math.acos(max(-1.0, min(1.0, cosine)))
        # Positive- and negative-knee solutions; the calf joint zero includes a -2.4 rad fixed offset.
        solutions = []
        for b in (-bend, bend):
            theta = math.atan2(-x, -z_prime)
            a = theta - math.atan2(self.l3 * math.sin(b), self.l2 + self.l3 * math.cos(b))
            q2 = a - self.thigh_origin_pitch
            q3 = b - self.calf_origin_pitch
            q = np.array([q1, q2, q3], dtype=float)
            if all(lo <= value <= hi for value, (lo, hi) in zip(q, (self.hip_limit, self.thigh_limit, self.calf_limit))):
                if np.linalg.norm(self.forward(q, is_right_leg) - p) < 1e-6:
                    solutions.append(q)
        if not solutions:
            return None
        # Prefer the established nominal knee bending side (fixed calf pitch -2.4).
        return min(solutions, key=lambda a: (abs(a[2] - 1.2), abs(a[1] + 0.6)))
