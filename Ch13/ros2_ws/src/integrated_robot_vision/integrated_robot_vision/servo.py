"""Conservative two-axis image servo, independent of ROS and command transport."""
import math

import numpy as np


CONTROL_JOINTS = ('arm_joint_1', 'arm_joint_5')


def project_target(chain, q, target_base, k):
    return _camera_point(chain.forward(q), target_base, k)[0]


def _camera_point(camera, target_base, k):
    target = np.asarray(target_base, dtype=float)
    if target.shape != (3,) or not np.isfinite(target).all():
        raise ValueError('finite base-frame target required')
    point = camera[:3, :3].T @ (target - camera[:3, 3])
    if not .1 <= point[2] <= 5.:
        raise ValueError('target outside camera depth range')
    return np.array([k.fx * point[0] / point[2] + k.cx,
                     k.fy * point[1] / point[2] + k.cy]), point


def projection_jacobian(chain, q, target_base, k, joints=CONTROL_JOINTS):
    if joints != CONTROL_JOINTS:
        raise ValueError('canonical two-axis control order required')
    return _projection_and_jacobian(chain,q,target_base,k)[1]


def _projection_and_jacobian(chain,q,target_base,k):
    camera, axes = chain.camera_kinematics(q)
    pixel, point = _camera_point(camera,target_base,k)
    x,y,z = point
    projection = np.array([[k.fx/z,0.,-k.fx*x/z**2],
                           [0.,k.fy/z,-k.fy*y/z**2]])
    columns=[]
    for name in CONTROL_JOINTS:
        axis,origin,kind = axes[name]
        # Inverse camera motion for a stationary base-frame target.
        derivative = (-axis if kind == 'prismatic' else
                      -np.cross(axis,np.asarray(target_base)-origin))
        columns.append(projection @ camera[:3,:3].T @ derivative)
    return pixel,np.column_stack(columns)


def servo_target(chain, q, target_base, k, dt):
    if not math.isfinite(dt) or dt <= 0:
        return None
    try:
        pixel,jacobian = _projection_and_jacobian(chain,q,target_base,k)
        if not (0 <= pixel[0] < k.width and 0 <= pixel[1] < k.height):
            return None
        singular = np.linalg.svd(jacobian, compute_uv=False)
        if singular[-1] < 1e-6 or singular[0] / singular[-1] > 100:
            return None
        error = np.array([k.cx, k.cy]) - pixel
        step = .5 * jacobian.T @ np.linalg.solve(
            jacobian @ jacobian.T + .01**2 * np.eye(2), error)
        desired = q.copy()
        maximum_step = .10 * min(dt, .2)
        for name, delta in zip(CONTROL_JOINTS, step):
            if abs(q[name]) > .04 + 1e-12:
                return None
            desired[name] = float(np.clip(
                q[name] + np.clip(delta, -maximum_step, maximum_step), -.04, .04))
        return desired
    except (ValueError, KeyError, TypeError, np.linalg.LinAlgError):
        return None


def camera_motion_target(q, elapsed, dt=.2):
    """Explicit test fixture ONLY: q1 sine (.03rad, 2s), never a tracking fallback."""
    names = tuple(f'arm_joint_{i}' for i in range(1, 7))
    if (not math.isfinite(elapsed) or elapsed < 0 or not math.isfinite(dt) or dt <= 0
            or any(n not in q or not math.isfinite(q[n]) or abs(q[n]) >= .06 for n in names)
            or any(abs(q[n]) > .04+1e-12 for n in CONTROL_JOINTS)):
        return None
    horizon = min(dt, .2)
    desired = q.copy()
    nominal = .03*math.sin(math.pi*(elapsed+horizon))
    delta = float(np.clip(nominal-q['arm_joint_1'], -.10*horizon, .10*horizon))
    desired['arm_joint_1'] = float(np.clip(q['arm_joint_1']+delta, -.03, .03))
    return desired
