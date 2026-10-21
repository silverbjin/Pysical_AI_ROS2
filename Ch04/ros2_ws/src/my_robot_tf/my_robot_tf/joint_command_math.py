"""4.7절 시뮬레이션 위치 명령의 정적 안전 범위."""

import math

JOINT_LIMITS = {"joint1": 3.14, "joint2": 1.57}


def target_position(joint_name, positive, amplitude=0.785):
    """관절 명칭과 제한을 확인하고 ±목표각(rad)을 생성한다."""
    if joint_name not in JOINT_LIMITS:
        raise ValueError(f"Unsupported joint: {joint_name}")
    if not math.isfinite(amplitude) or amplitude < 0:
        raise ValueError("amplitude must be finite and nonnegative")
    limited = min(amplitude, JOINT_LIMITS[joint_name])
    return limited if positive else -limited
