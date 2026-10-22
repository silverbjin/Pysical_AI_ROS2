"""No missing-model download or fixture fallback; preserve capture headers."""
import hashlib
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from std_msgs.msg import Header

from integrated_robot_vision.contracts import Box2D
from integrated_robot_vision.detectors import (
    ColorFixtureBackend, YoloBackend, to_detection_array, verify_asset,
)


def test_missing_weights_fail_before_model_import(tmp_path):
    with pytest.raises(FileNotFoundError):
        YoloBackend(tmp_path / 'missing.pt')
    package = Path(__file__).resolve().parents[1]
    code = (f'import sys; sys.path.insert(0,{str(package)!r}); '
            'from pathlib import Path; from integrated_robot_vision.detectors import YoloBackend; '
            '\ntry: YoloBackend(Path("/nonexistent-ch13-4-model.pt"))'
            '\nexcept FileNotFoundError: pass'
            '\nelse: raise AssertionError("missing model accepted")'
            '\nassert "torch" not in sys.modules and "ultralytics" not in sys.modules')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_asset_hash_mismatch_rejected(tmp_path):
    asset = tmp_path / 'trusted-test.bin'
    asset.write_bytes(b'abc')
    verify_asset(asset, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    with pytest.raises(ValueError):
        verify_asset(asset, '0' * 64)
    with pytest.raises(ValueError):
        verify_asset(asset, '')


def test_fixture_red_box_and_header_preserved():
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    image[10:30, 20:40, 2] = 255
    boxes = ColorFixtureBackend().detect(image)
    assert len(boxes) == 1
    box = boxes[0]
    assert (box.cx, box.cy, box.width, box.height) == (29.5, 19.5, 20., 20.)
    assert box.class_id == 'fixture_red'
    header = Header(frame_id='camera_optical_frame')
    header.stamp.sec, header.stamp.nanosec = 1, 23
    output = to_detection_array(boxes, header, image_size=(100, 80))
    assert output.header == header
    assert output.detections[0].header == header
    assert output.detections[0].results[0].hypothesis.class_id == 'fixture_red'
    header.stamp.sec = 99
    assert output.header.stamp.sec == 1


def test_empty_and_clipped_results_do_not_invent_detections():
    backend = ColorFixtureBackend()
    assert backend.detect(np.zeros((80, 100, 3), dtype=np.uint8)) == []
    header = Header(frame_id='camera_optical_frame')
    header.stamp.sec = 1
    output = to_detection_array([Box2D(0, 5, 6, 4, '5', .8),
                                 Box2D(-10, 5, 2, 2, '5', .9)], header, image_size=(10, 10))
    assert len(output.detections) == 1
    assert output.detections[0].bbox.center.position.x == 1.5
    assert output.detections[0].bbox.size_x == 3.
    assert to_detection_array([], header).detections == []


@pytest.mark.parametrize('image', [np.zeros((10, 10)), np.zeros((10, 10, 4), np.uint8),
                                  np.zeros((10, 10, 3), np.float32)])
def test_backend_rejects_non_bgr8_input(image):
    with pytest.raises(ValueError):
        ColorFixtureBackend().detect(image)
