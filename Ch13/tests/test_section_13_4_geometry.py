"""Catch unit/stride/bounds bugs before invalid depth becomes a motor target."""
import struct

import numpy as np
import pytest

from integrated_robot_vision.contracts import Box2D, Intrinsics, Observation
from integrated_robot_vision.geometry import (
    decode_depth, deproject, sample_depth, transform_point,
)


def intrinsics(**changes):
    args = dict(width=100, height=100, fx=100., fy=100., cx=50., cy=50.,
                frame_id='camera_optical_frame', calibration_id='test')
    return Intrinsics(**(args | changes))


def test_mm_and_float_depth_project_same_point():
    mm = decode_depth(struct.pack('<H', 1000), '16UC1', 1, 1, 2, False)
    meters = decode_depth(struct.pack('<f', 1.), '32FC1', 1, 1, 4, False)
    np.testing.assert_allclose(deproject(60, 50, mm[0, 0], intrinsics()), [.1, 0, 1])
    np.testing.assert_allclose(deproject(60, 50, meters[0, 0], intrinsics()), [.1, 0, 1])


def test_padded_big_endian_depth():
    data = bytes.fromhex('03e8 07d0 ffff 0bb8 0fa0 ffff')
    decoded = decode_depth(data, '16UC1', 2, 2, 6, True)
    np.testing.assert_allclose(decoded, [[1, 2], [3, 4]])
    decoded[0, 0] = 9  # result must be a writable independent array
    assert data[:2] == bytes.fromhex('03e8')


@pytest.mark.parametrize('depth', [0, -1, np.nan, np.inf, .099, 5.001])
def test_invalid_depth_and_intrinsics_rejected(depth):
    with pytest.raises(ValueError):
        deproject(50, 50, depth, intrinsics())


@pytest.mark.parametrize('changes', [dict(fx=0), dict(fy=-1), dict(cx=np.nan),
                                    dict(width=0), dict(frame_id=''), dict(calibration_id='')])
def test_invalid_calibration_rejected(changes):
    with pytest.raises(ValueError):
        deproject(50, 50, 1, intrinsics(**changes))


@pytest.mark.parametrize('u,v', [(-1, 0), (100, 0), (0, 100), (np.nan, 0)])
def test_pixels_outside_image_rejected(u, v):
    with pytest.raises(ValueError):
        deproject(u, v, 1, intrinsics())


@pytest.mark.parametrize('encoding,w,h,step,data', [
    ('8UC1', 1, 1, 1, b'\x01'), ('16UC1', 2, 1, 2, b'\x00\x00'),
    ('32FC1', 1, 1, 4, b'\x00'), ('16UC1', 1, 1, 2, b'\x00\x00\x00'),
    ('16UC1', 0, 1, 2, b'\x00\x00'), ('16UC1', 1, -1, 2, b''),
])
def test_malformed_depth_bytes_rejected(encoding, w, h, step, data):
    with pytest.raises(ValueError):
        decode_depth(data, encoding, w, h, step, False)


def test_patch_minimum_and_background_rejection():
    box = Box2D(3, 3, 5, 5, 'fixture_red', .9)
    depth = np.zeros((7, 7))
    depth[2, 1:6] = 1
    assert sample_depth(depth, box) == (1., 0.)
    depth[2, 1] = 0
    with pytest.raises(ValueError):
        sample_depth(depth, box)
    depth[1:6, 1:6] = np.arange(25).reshape(5, 5) / 10 + 1
    with pytest.raises(ValueError):
        sample_depth(depth, box)


def test_patch_clips_to_bbox_and_excludes_nonfinite():
    depth = np.full((9, 9), 4.)
    depth[3:6, 3:6] = 1.
    depth[3, 3] = np.nan
    depth[3, 4] = np.inf
    assert sample_depth(depth, Box2D(4, 4, 3, 3, 'x', .9)) == (1., 0.)
    with pytest.raises(ValueError):
        sample_depth(depth, Box2D(-20, 4, 3, 3, 'x', .9))


def test_transform_uses_translation_and_rejects_nonrigid():
    matrix = np.array([[0, -1, 0, 1], [1, 0, 0, 2], [0, 0, 1, 3], [0, 0, 0, 1.]])
    np.testing.assert_allclose(transform_point(np.array([1, 0, 2]), matrix), [1, 3, 5])
    matrix[0, 0] = 2
    with pytest.raises(ValueError):
        transform_point(np.array([1, 0, 2]), matrix)


def test_observation_copies_arrays_and_rejects_bad_covariance():
    point, cov = np.ones(3), np.eye(3)
    obs = Observation(1., 0, 'cal', 'odom', Box2D(1, 1, 2, 2, 'x', .9), point, cov)
    point[0] = 9
    assert obs.point[0] == 1
    assert not obs.point.flags.writeable
    with pytest.raises(ValueError):
        Observation(1., 0, 'cal', 'odom', obs.box, point, -cov)
