"""ROS 없이 테스트할 수 있는 4.1절 TF 프레임 계약 검증기."""

import math


def validate_frame_tree(edges):
    """(parent, child) 목록의 단일 부모·무순환 계약을 검증한다.

    별도 루트가 있는 *forest*도 허용한다. 값이 유효하면 True를 반환한다.
    """
    parents = {}
    for parent, child in edges:
        if not isinstance(parent, str) or not isinstance(child, str):
            raise ValueError("frame id must be a string")
        if not parent.strip() or not child.strip():
            raise ValueError("frame id must not be empty")
        if parent == child:
            raise ValueError("frame cannot be its own parent")
        if child in parents and parents[child] != parent:
            raise ValueError("a child cannot have two parents")
        parents[child] = parent

    for child in parents:
        visited = set()
        cursor = child
        while cursor in parents:
            if cursor in visited:
                raise ValueError("TF tree contains a cycle")
            visited.add(cursor)
            cursor = parents[cursor]
    return True


def is_unit_quaternion(x, y, z, w, atol=1e-6):
    """(x, y, z, w) 쿼터니언의 유한성·단위 길이를 검사한다."""
    values = (x, y, z, w)
    if not all(math.isfinite(v) for v in values):
        return False
    return abs(sum(v * v for v in values) - 1.0) <= atol
