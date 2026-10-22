"""Depth decoding and optical geometry. Depth is axial Z, not ray range."""
import math

import numpy as np

from .contracts import Box2D, Intrinsics, finite, vector


def decode_depth(data: bytes, encoding: str, width: int, height: int,
                 step: int, big_endian: bool) -> np.ndarray:
    if encoding not in ('16UC1', '32FC1'):
        raise ValueError('only aligned 16UC1/32FC1 supported')
    if any(type(v) is not int or v <= 0 for v in (width, height, step)):
        raise ValueError('positive integer dimensions/step required')
    dtype = np.dtype(('>' if big_endian else '<') + ('u2' if encoding == '16UC1' else 'f4'))
    if step < width * dtype.itemsize or len(data) != height * step:
        raise ValueError('invalid image stride or payload length')
    result = np.ndarray((height, width), dtype=dtype, buffer=data,
                        strides=(step, dtype.itemsize)).astype(np.float64)
    if encoding == '16UC1':
        result *= .001
    return result


def validate_depth_range(min_depth_m: float, max_depth_m: float) -> None:
    finite(min_depth_m, max_depth_m)
    if not 0 < min_depth_m < max_depth_m:
        raise ValueError('positive ordered depth bounds required')


def sample_depth(depth: np.ndarray, box: Box2D, min_valid: int = 5, *,
                 min_depth_m: float = .1, max_depth_m: float = 5.) -> tuple[float, float]:
    validate_depth_range(min_depth_m, max_depth_m)
    depth = np.asarray(depth)
    if depth.ndim != 2 or type(min_valid) is not int or min_valid < 1:
        raise ValueError('2D depth and positive sample count required')
    height, width = depth.shape
    if not (0 <= box.cx < width and 0 <= box.cy < height):
        raise ValueError('box center outside image')
    u, v = math.floor(box.cx + .5), math.floor(box.cy + .5)
    left = max(0, u - 2, math.ceil(box.cx - box.width / 2))
    right = min(width, u + 3, math.floor(box.cx + box.width / 2) + 1)
    top = max(0, v - 2, math.ceil(box.cy - box.height / 2))
    bottom = min(height, v + 3, math.floor(box.cy + box.height / 2) + 1)
    patch = depth[top:bottom, left:right]
    valid = patch[np.isfinite(patch) & (patch >= min_depth_m) & (patch <= max_depth_m)]
    if len(valid) < min_valid:
        raise ValueError('insufficient valid depth samples')
    median = float(np.median(valid))
    mad = float(np.median(np.abs(valid - median)))
    if mad > .03:
        raise ValueError('depth discontinuity: MAD exceeds 0.03 m')
    return median, mad


def deproject(u: float, v: float, depth_m: float, k: Intrinsics, *,
              min_depth_m: float = .1, max_depth_m: float = 5.) -> np.ndarray:
    validate_depth_range(min_depth_m, max_depth_m)
    finite(u, v, depth_m)
    if not (0 <= u < k.width and 0 <= v < k.height and min_depth_m <= depth_m <= max_depth_m):
        raise ValueError('pixel or depth outside calibrated limits')
    return np.array([(u-k.cx)*depth_m/k.fx, (v-k.cy)*depth_m/k.fy, depth_m])


def transform_point(point: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    point = vector(point, (3,))
    matrix = vector(matrix, (4, 4))
    rotation = matrix[:3, :3]
    if (not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-9)
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-9)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-9)):
        raise ValueError('rigid proper homogeneous transform required')
    return rotation @ point + matrix[:3, 3]
