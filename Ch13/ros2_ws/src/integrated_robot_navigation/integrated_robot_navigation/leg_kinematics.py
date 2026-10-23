"""Three-axis leg IK from verified URDF geometry; never clips unreachable feet."""
from functools import lru_cache
import math
import xml.etree.ElementTree as ET

import numpy as np
from integrated_robot_vision.kinematics import origin_matrix

from .model import ModelContract
from .samples import Vec3


def fk_leg(model: ModelContract, foot: str, q: Vec3) -> Vec3:
    if foot not in model.feet:
        raise ValueError('unknown foot')
    values = np.asarray(q, dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all():
        raise ValueError('three finite joint angles required')
    try:
        hip, offset, upper, lower, names = _leg_spec(model.urdf, foot)
    except ValueError:
        # FK still supports general URDF axes/origins. Only verified scalar
        # Rx/Ry/Ry geometry gets the fast path; IK keeps its stricter contract.
        pass
    else:
        if any(not model.limits[name][0] <= value <= model.limits[name][1]
               for name, value in zip(names, values)):
            raise ValueError('joint position outside limits')
        roll, thigh, knee = values
        x = -upper*math.sin(thigh)-lower*math.sin(thigh+knee)
        z = -upper*math.cos(thigh)-lower*math.cos(thigh+knee)
        c, s = math.cos(roll), math.sin(roll)
        return (float(hip[0]+x), float(hip[1]+offset*c-z*s), float(hip[2]+offset*s+z*c))
    names = tuple(foot[:2] + '_' + p + '_joint' for p in ('hip', 'thigh', 'calf'))
    joint_map = dict(zip(names, values))
    base = model.chains['base_link'].forward(joint_map)
    result = np.linalg.solve(base, model.chains[foot].forward(joint_map))
    return tuple(float(v) for v in result[:3, 3])


@lru_cache(maxsize=32)
def _leg_spec(urdf: str, foot: str):
    tree = ET.fromstring(urdf)
    all_joints = {j.get('name'): j for j in tree.findall('joint')}
    names = tuple(foot[:2] + '_' + p + '_joint' for p in ('hip', 'thigh', 'calf'))
    joints = [all_joints[n] for n in names]
    origins = [origin_matrix(j.find('origin')) for j in joints]
    terminal = next(j for j in all_joints.values() if j.find('child').get('link') == foot)
    last = origin_matrix(terminal.find('origin'))
    expected_axes = ((1., 0., 0.), (0., 1., 0.), (0., 1., 0.))
    for joint, transform, expected in zip(joints, origins, expected_axes):
        axis = tuple(float(v) for v in joint.find('axis').get('xyz').split())
        if (joint.get('type') != 'revolute' or axis != expected
                or not np.allclose(transform[:3, :3], np.eye(3), atol=1e-12)):
            raise ValueError('unsupported leg geometry: axis or origin rotation')
    hip, thigh, calf = [t[:3, 3] for t in origins]
    tip = last[:3, 3]
    if (joints[0].find('parent').get('link') != 'base_link'
            or not np.allclose(thigh[[0, 2]], 0., atol=1e-12)
            or not np.allclose(calf[:2], 0., atol=1e-12)
            or not np.allclose(tip[:2], 0., atol=1e-12)
            or not np.allclose(last[:3, :3], np.eye(3), atol=1e-12)
            or terminal.get('type') != 'fixed' or calf[2] >= 0 or tip[2] >= 0):
        raise ValueError('unsupported leg geometry: link offsets')
    return hip, float(thigh[1]), float(-calf[2]), float(-tip[2]), names


def ik_leg(model: ModelContract, foot: str, p: Vec3, previous: Vec3) -> Vec3:
    if foot not in model.feet:
        raise ValueError('unknown foot')
    target, previous_array = np.asarray(p, dtype=float), np.asarray(previous, dtype=float)
    if (target.shape != (3,) or previous_array.shape != (3,)
            or not np.isfinite(target).all() or not np.isfinite(previous_array).all()):
        raise ValueError('finite target and previous angles required')
    fk_leg(model, foot, previous)  # validate the measured reference against real limits
    hip, offset, upper, lower, names = _leg_spec(model.urdf, foot)
    x, y, z = target - hip
    radial_squared = y*y + z*z - offset*offset
    if radial_squared <= 0:
        raise ValueError('unreachable hip offset')
    solutions = []
    # Both radial branches are considered; the actual joint limits reject unsafe folds.
    for local_z in (-math.sqrt(radial_squared), math.sqrt(radial_squared)):
        hip_angle = math.atan2(z, y) - math.atan2(local_z, offset)
        hip_angle = math.atan2(math.sin(hip_angle), math.cos(hip_angle))
        cosine = (x*x + local_z*local_z - upper*upper - lower*lower) / (2*upper*lower)
        if cosine < -1. - 1e-12 or cosine > 1. + 1e-12:
            continue
        # Roundoff at an analytic boundary, not workspace/joint-limit clipping.
        knee_abs = math.acos(min(1., max(-1., cosine)))
        for knee in (knee_abs, -knee_abs):
            thigh = math.atan2(-x, -local_z) - math.atan2(
                lower*math.sin(knee), upper + lower*math.cos(knee))
            thigh_lo, thigh_hi = model.limits[names[1]][:2]
            first_turn = math.ceil((thigh_lo - thigh) / math.tau)
            last_turn = math.floor((thigh_hi - thigh) / math.tau)
            for turn in range(first_turn, last_turn + 1):
                q = (hip_angle, thigh + turn * math.tau, knee)
                if all(model.limits[n][0] <= value <= model.limits[n][1]
                       for n, value in zip(names, q)):
                    if np.linalg.norm(np.asarray(fk_leg(model, foot, q)) - target) < 1e-8:
                        solutions.append(q)
    if not solutions:
        raise ValueError('unreachable target or joint limit')
    return min(solutions, key=lambda q: sum((a-b)**2 for a, b in zip(q, previous_array)))
