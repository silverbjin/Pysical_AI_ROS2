import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2_ws/src/integrated_robot_runtime'))
from integrated_robot_runtime.policy import joint_snapshot, safe_arm, validate_target, valid_pair


def test_joint_snapshot_rejects_partial_duplicate_and_nonfinite_states():
    assert joint_snapshot(['a', 'b'], [0.1, 0.2], ['b', 'a']) == [0.2, 0.1]
    for names, values in [(['a'], [0]), (['a', 'a', 'b'], [0, 0, 0]),
                          (['a', 'b'], [0, math.nan]), (['a', 'b'], [0])]:
        assert joint_snapshot(names, values, ['a', 'b']) is None


def test_stow_gate_requires_fresh_measured_safe_arm():
    assert safe_arm([0] * 6, 0.1)
    assert not safe_arm([0] * 6, 0.51)
    assert not safe_arm([0] * 5, 0.1)
    assert not safe_arm([0, 0.2, 0, 0, 0, 0], 0.1)
    assert not safe_arm([math.nan] * 6, 0.1)


@pytest.mark.parametrize('image,odom,now,want', [
    (10.0, 10.04, 10.1, True), (10.0, 10.06, 10.1, False),
    (10.0, 10.01, 10.4, False), (11.0, 11.01, 10.0, False),
    (0, 0, 0, False), (math.nan, 10.0, 10.1, False),
])
def test_sync_rejects_skew_stale_future_and_zero_stamps(image, odom, now, want):
    assert valid_pair(image, odom, now) is want


def test_pick_contract_preserves_frame_age_and_refuses_unimplemented_execution():
    assert validate_target('cup', 'base_link', 10.0, 10.1, [0.3, 0, 0.4], [0, 0, 0, 1], True) == ''
    assert validate_target('', 'base_link', 10, 10.1, [0, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', '', 10, 10.1, [0, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', 'map', 10, 10.1, [0, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', 'base_link', 1, 10.1, [0, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', 'base_link', 10, 10.1, [math.nan, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', 'base_link', 10, 10.1, [0, 0, 0], [0, 0, 0, 0], True)
    assert validate_target('cup', 'base_link', 10, 10.1, [0, 0, 0], [0, 0, 0, 1], False)


def test_pick_allows_small_clock_delivery_skew_but_rejects_future_beyond_50ms():
    assert not validate_target('cup', 'base_link', 10.02, 10.0, [0, 0, 0], [0, 0, 0, 1], True)
    assert validate_target('cup', 'base_link', 10.1, 10.0, [0, 0, 0], [0, 0, 0, 1], True)
