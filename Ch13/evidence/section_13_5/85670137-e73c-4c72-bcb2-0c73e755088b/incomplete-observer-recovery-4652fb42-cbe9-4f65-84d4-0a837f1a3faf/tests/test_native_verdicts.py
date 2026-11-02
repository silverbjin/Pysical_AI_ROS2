"""Acceptance arithmetic is not native evidence; these are unit-only fixtures."""
import importlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))


def api():
    assert importlib.util.find_spec('verify_navigation_13_5'), 'native acceptance assessor missing'
    return importlib.import_module('verify_navigation_13_5')


@pytest.mark.parametrize('distance,expected', [(.40, True), (.350001, True), (.349999, False)])
def test_forward_measured_error_boundary(distance, expected):
    result = api().motion_phase((0., 0., 0.), (distance, 0., 0.), 'forward')
    assert result['passed'] is expected


@pytest.mark.parametrize('yaw,drift,expected', [(.30, .049999, True),
                                              (.199999, 0., False), (.30, .050001, False)])
def test_measured_yaw_error_and_drift_boundary(yaw, drift, expected):
    assert api().motion_phase((0., 0., 0.), (drift, 0., yaw), 'left')['passed'] is expected


def test_reverse_and_right_have_real_direction_not_absolute_distance():
    verify = api()
    assert verify.motion_phase((0., 0., 0.), (-.10, 0., 0.), 'reverse')['passed']
    assert not verify.motion_phase((0., 0., 0.), (.10, 0., 0.), 'reverse')['passed']
    assert verify.motion_phase((0., 0., 0.), (0., 0., -.30), 'right')['passed']
    assert not verify.motion_phase((0., 0., 0.), (0., 0., .30), 'right')['passed']


@pytest.mark.parametrize('source', ['command_integrated', 'synthetic', ''])
def test_command_log_or_fake_odometry_cannot_pass_crawl(source):
    from integrated_robot_navigation.carry_profile import default_limits
    checks = api().assess_crawl(dict(root_source=source, commands=[(.01, 0., 0.)]*100), default_limits())
    assert not all(checks.values()) and not checks['native_observations']


def test_missing_contact_or_native_com_never_passes():
    from integrated_robot_navigation.carry_profile import default_limits
    checks = api().assess_crawl(dict(root_source='native_ground_truth', frames=[{}]), default_limits())
    assert not checks['contact_support'] and not checks['native_com_consistent']
