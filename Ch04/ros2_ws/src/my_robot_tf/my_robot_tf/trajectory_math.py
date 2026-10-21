"""4.3절 원운동 기하학 (ROS 없이 단위 테스트 가능)."""

import math


def circle_pose(radius, angle):
    """월드 기준 원운동 x, y와 접선 방향 yaw(rad)를 계산한다."""
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("radius must be finite and positive")
    if not math.isfinite(angle):
        raise ValueError("angle must be finite")
    return radius * math.cos(angle), radius * math.sin(angle), angle + math.pi / 2


def yaw_quaternion(yaw):
    """yaw(rad)를 ROS의 xyzw 쿼터니언으로 변환한다."""
    if not math.isfinite(yaw):
        raise ValueError("yaw must be finite")
    return (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))
