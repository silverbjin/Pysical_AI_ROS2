"""Pure-static 7.5 tests; runnable without ROS."""
import math
import pytest

from vision_basics.projection_math import back_project


def test_center_pixel():
    assert back_project(320, 240, 1.0, 600, 600, 320, 240) == (0.0, 0.0, 1.0)


def test_offset_and_depth():
    assert back_project(380, 300, 2.0, 600, 600, 320, 240) == (0.2, 0.2, 2.0)


@pytest.mark.parametrize('z', [0.0, -1.0, math.nan, math.inf, 6.0])
def test_invalid_depth_fails_closed(z):
    with pytest.raises(ValueError):
        back_project(320, 240, z, 600, 600, 320, 240)


def test_invalid_calibration():
    with pytest.raises(ValueError):
        back_project(320, 240, 1.0, 0, 600, 320, 240)
