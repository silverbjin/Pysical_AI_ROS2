"""ROS-free tests of wave profile and guarded startup contract."""
import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'manipulation_basics'
spec = importlib.util.spec_from_file_location('profile', PKG / 'wave_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def test_syntax_for_publisher_profile_and_launch():
    for path in [PKG / 'wave_profile.py', PKG / 'wave_hello_node.py',
                 ROOT / 'launch/wave_hello.launch.py']:
        compile(ast.parse(path.read_text()), str(path), 'exec')


def test_bounds_by_amplitude_and_angular_velocity():
    for i in range(501):
        positions, speeds = profile.wave_target(i / 10)
        assert abs(positions[0]) <= 0.22 + 1e-9
        assert abs(positions[3]) <= 0.28 + 1e-9
        assert abs(speeds[0]) <= 0.22 * 0.8 + 1e-9
        assert abs(speeds[3]) <= 0.28 * 2 + 1e-9


def test_ready_pose_requires_all_valid_joints():
    assert profile.pose_reached(profile.READY_POSE)
    assert not profile.pose_reached((0, -0.5, 0.8))
    assert not profile.pose_reached((0, -0.5, float('nan'), 0))
    assert not profile.pose_reached((0, 0, 0, 0))


@pytest.mark.parametrize('elapsed,lookahead', [(-1, .15), (1, -1), (float('nan'), .15),
                                               (float('inf'), .15)])
def test_invalid_timestamps_rejected(elapsed, lookahead):
    with pytest.raises(ValueError):
        profile.wave_target(elapsed, lookahead)


def test_publisher_has_feedback_safety_and_sim_time_launch():
    source = (PKG / 'wave_hello_node.py').read_text()
    launch = (ROOT / 'launch/wave_hello.launch.py').read_text()
    assert 'pose_reached(self.latest_joint_positions)' in source
    assert 'now - self.last_state_time > 0.5' in source
    assert 'self.pub.get_subscription_count() == 0' in source
    assert "'use_sim_time': True" in launch
