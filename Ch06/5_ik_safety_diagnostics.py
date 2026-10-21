"""2-DOF Jacobian diagnostics (no ROS, no motor commands).

A *bounded demonstration* of a damped least-squares step for diagnosing
near singularities, unreachable targets and joint limits.
"""
import argparse
import json
import math

L1 = L2 = 0.5


def forward(theta):
    a, b = theta
    return (L1 * math.cos(a) + L2 * math.cos(a + b),
            L1 * math.sin(a) + L2 * math.sin(a + b))


def jacobian(theta):
    a, b = theta
    return ((-L1 * math.sin(a) - L2 * math.sin(a + b), -L2 * math.sin(a + b)),
            (L1 * math.cos(a) + L2 * math.cos(a + b), L2 * math.cos(a + b)))


def diagnose(theta, goal, damping=0.05, max_step=0.15, limits=(-math.pi, math.pi)):
    """Single bounded numerical step; not a complete robot IK solution."""
    if damping <= 0 or max_step <= 0 or limits[0] >= limits[1]:
        raise ValueError("invalid damping, max_step or limits")
    if len(theta) != 2 or len(goal) != 2:
        raise ValueError("expected two angles and a 2D goal")
    if not all(math.isfinite(v) for v in (*theta, *goal)):
        raise ValueError("all input values must be finite")

    xy = forward(theta)
    error = (goal[0] - xy[0], goal[1] - xy[1])
    err = math.hypot(*error)
    j = jacobian(theta)
    a, b = j[0]
    c, d = j[1]
    trace = a * a + b * b + c * c + d * d
    detj = a * d - b * c
    disc = math.sqrt(max(trace * trace - 4 * detj * detj, 0.0))
    sigma_min = math.sqrt(max((trace - disc) / 2, 0.0))
    sigma_max = math.sqrt(max((trace + disc) / 2, 0.0))
    condition = None if sigma_min <= 1e-12 else sigma_max / sigma_min
    # J^T J + lambda^2 I, a positive-definite 2x2 system.
    aa, ab = a * a + c * c + damping ** 2, a * b + c * d
    bb = b * b + d * d + damping ** 2
    rhs1, rhs2 = a * error[0] + c * error[1], b * error[0] + d * error[1]
    determinant = aa * bb - ab * ab
    delta1 = (bb * rhs1 - ab * rhs2) / determinant
    delta2 = (aa * rhs2 - ab * rhs1) / determinant
    norm = math.hypot(delta1, delta2)
    if norm > max_step:
        scale = max_step / norm
        delta1 *= scale
        delta2 *= scale
    candidate = (min(limits[1], max(limits[0], theta[0] + delta1)),
                 min(limits[1], max(limits[0], theta[1] + delta2)))
    reachable = math.hypot(*goal) <= L1 + L2 + 1e-9
    if not reachable:
        verdict = "UNREACHABLE"
    elif sigma_min < 1e-5:
        verdict = "NEAR_SINGULAR"
    elif candidate == tuple(theta) and err > 1e-3:
        verdict = "STALLED"
    else:
        verdict = "STEP_COMPUTED"
    return {
        "verdict": verdict,
        "residual_m": err,
        "min_singular_value": sigma_min,
        "jacobian_condition": condition,
        "step_rad": [delta1, delta2],
        "next_joint_rad": list(candidate),
        "limited": any(abs(candidate[i] - theta[i] - (delta1, delta2)[i]) > 1e-10
                       for i in range(2)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joint", nargs=2, type=float, default=[0.0, 0.0])
    parser.add_argument("--target", nargs=2, type=float, default=[0.7, 0.0])
    args = parser.parse_args()
    result = diagnose(args.joint, args.target)
    print(json.dumps(result, indent=2, allow_nan=False, default=str))
    return 1 if result["verdict"] == "UNREACHABLE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
