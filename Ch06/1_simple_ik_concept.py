"""Planar two-link IK teaching example (metres, radians).

Damped least squares and a bounded step limit numerical instability.
This is NOT a robot motion controller: no joint, collision, or timing limits.
"""
import math
import numpy as np

L1, L2 = 0.5, 0.5


def forward_kinematics(theta1, theta2):
    return np.array([
        L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2),
        L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2),
    ], dtype=float)


def compute_jacobian(theta1, theta2):
    s1 = math.sin(theta1)
    s12 = math.sin(theta1 + theta2)
    c1 = math.cos(theta1)
    c12 = math.cos(theta1 + theta2)
    return np.array([
        [-L1 * s1 - L2 * s12, -L2 * s12],
        [L1 * c1 + L2 * c12, L2 * c12],
    ], dtype=float)


def inverse_kinematics_numerical(
    target_x, target_y, init_theta1=0.1, init_theta2=0.1,
    *, tolerance=0.001, max_iter=200, gain=0.5,
    damping=0.05, max_step=0.25,
):
    """Find joint angles, or return None on invalid/unreachable/nonconvergent targets.

    DLS: (J.T J + lambda^2 I) delta = J.T error.
    The residual is verified with FK before declaring convergence.
    """
    target = np.array([target_x, target_y], dtype=float)
    theta = np.array([init_theta1, init_theta2], dtype=float)
    if not np.all(np.isfinite(target)) or not np.all(np.isfinite(theta)):
        raise ValueError("target and initial angles must be finite")
    if (tolerance <= 0 or max_iter <= 0 or
            not 0 < gain <= 1 or damping <= 0 or max_step <= 0):
        raise ValueError("invalid solver parameters")

    radius = float(np.linalg.norm(target))
    if radius > L1 + L2 + tolerance or radius < abs(L1 - L2) - tolerance:
        print("IK REJECTED: target lies outside geometric workspace")
        return None

    for iteration in range(max_iter):
        residual = target - forward_kinematics(*theta)
        error = float(np.linalg.norm(residual))
        if error < tolerance:
            print(
                f"Converged iter={iteration}, residual={error:.6f} m, "
                f"joint1={math.degrees(theta[0]):.2f} deg, "
                f"joint2={math.degrees(theta[1]):.2f} deg"
            )
            return theta
        jacobian = compute_jacobian(*theta)
        update = np.linalg.solve(
            jacobian.T @ jacobian + (damping ** 2) * np.eye(2),
            jacobian.T @ residual,
        )
        step_norm = float(np.linalg.norm(update))
        if step_norm > max_step:
            update *= max_step / step_norm
        theta += gain * update
    final_error = float(np.linalg.norm(target - forward_kinematics(*theta)))
    print(f"IK FAILED: max_iter={max_iter}, residual={final_error:.6f} m")
    return None


if __name__ == "__main__":
    result = inverse_kinematics_numerical(0.7, 0.0)
    if result is None:
        raise SystemExit(1)
