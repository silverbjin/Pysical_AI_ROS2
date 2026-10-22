"""Measured support geometry and mass-weighted kinematics, independent of ROS."""
import math

import numpy as np

from .model import ModelContract
from .samples import JointMap, Vec3


def support_margin(point: Vec3, contacts: list[Vec3]) -> float:
    p, points = np.asarray(point, dtype=float), np.asarray(contacts, dtype=float)
    if (p.shape != (3,) or points.ndim != 2 or points.shape[1] != 3
            or len(points) < 3 or not np.isfinite(p).all() or not np.isfinite(points).all()):
        raise ValueError('finite point and at least three contacts required')
    ordered = sorted(set(tuple(row[:2]) for row in points))
    if len(ordered) != len(points):
        raise ValueError('duplicate projected contact')

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    halves = []
    for sequence in (ordered, ordered[::-1]):
        half = []
        for contact in sequence:
            while len(half) >= 2 and cross(half[-2], half[-1], contact) <= 1e-12:
                half.pop()
            half.append(contact)
        halves.append(half[:-1])
    hull = halves[0] + halves[1]
    if len(hull) < 3:
        raise ValueError('degenerate support polygon')
    return float(min(cross(a, b, p) / math.hypot(b[0]-a[0], b[1]-a[1])
                     for a, b in zip(hull, hull[1:] + hull[:1])))


def center_of_mass(model: ModelContract, joints: JointMap, body_pose: object) -> Vec3:
    """body_pose is world_from_base_link, a rigid homogeneous 4x4 matrix."""
    pose = np.asarray(body_pose, dtype=float)
    if (pose.shape != (4, 4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3], (0., 0., 0., 1.), atol=1e-10)
            or not np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=1e-8)
            or not math.isclose(np.linalg.det(pose[:3, :3]), 1., abs_tol=1e-8)):
        raise ValueError('rigid body pose required')
    world_from_root = pose @ np.linalg.inv(model.chains['base_link'].forward(joints))
    total, moment = 0., np.zeros(3)
    for link, (mass, local_point) in model.masses.items():
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError('positive finite mass required')
        local = np.asarray((*local_point, 1.), dtype=float)
        if local.shape != (4,) or not np.isfinite(local).all():
            raise ValueError('finite inertial origin required')
        world = world_from_root @ model.chains[link].forward(joints) @ local
        total += mass
        moment += mass * world[:3]
    if total <= 0:
        raise ValueError('model mass is empty')
    return tuple(float(v) for v in moment / total)
