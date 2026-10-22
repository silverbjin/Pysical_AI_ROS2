"""The pinned native ideal camera leaves R unset; reject real distortion."""
import numpy as np
import pytest
from sensor_msgs.msg import CameraInfo

from integrated_robot_vision.camera_info_adapter import normalize_native_info


def native_info():
    msg = CameraInfo()
    msg.header.frame_id = 'camera_optical_frame'
    msg.header.stamp.sec = 4
    msg.width, msg.height = 320, 240
    msg.k = [277., 0., 160., 0., 277., 120., 0., 0., 1.]
    msg.p = [277., 0., 160., 0., 0., 277., 120., 0., 0., 0., 1., 0.]
    msg.d = [0.] * 5
    msg.distortion_model = 'plumb_bob'
    return msg


def test_normalize_pinned_ideal_camera_preserves_capture_and_intrinsics():
    msg = native_info()
    out = normalize_native_info(msg)
    assert out.header == msg.header
    assert list(out.k) == list(msg.k)
    assert list(out.p) == list(msg.p)
    np.testing.assert_array_equal(out.r, [1, 0, 0, 0, 1, 0, 0, 0, 1])
    np.testing.assert_array_equal(msg.r, np.zeros(9))


@pytest.mark.parametrize('bad_field', ['distortion', 'rotation', 'projection', 'frame', 'binning', 'roi'])
def test_native_metadata_adapter_does_not_repair_arbitrary_inputs(bad_field):
    msg = native_info()
    if bad_field == 'distortion':
        msg.d = [.1, 0., 0., 0., 0.]
    elif bad_field == 'rotation':
        msg.r = [2.] * 9
    elif bad_field == 'projection':
        msg.p[3] = .2
    elif bad_field == 'frame':
        msg.header.frame_id = 'another_camera'
    elif bad_field == 'binning':
        msg.binning_x = 2
    else:
        msg.roi.x_offset = 1
    with pytest.raises(ValueError):
        normalize_native_info(msg)
