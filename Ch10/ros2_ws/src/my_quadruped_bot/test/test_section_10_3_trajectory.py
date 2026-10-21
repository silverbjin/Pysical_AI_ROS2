"""Trajectory contract tests without ROS 2 or Gazebo."""
import numpy as np
import pytest
from my_quadruped_bot.trajectory_generator import TrajectoryGenerator


def test_swing_endpoints_and_apex():
    g = TrajectoryGenerator(step_height=0.05)
    a = np.array([0.0, 0.0, -0.30])
    b = np.array([0.10, 0.0, -0.30])
    np.testing.assert_allclose(g.generate_swing(a, b, 0.0), a)
    np.testing.assert_allclose(g.generate_swing(a, b, 1.0), b)
    assert g.generate_swing(a, b, 0.5)[2] == pytest.approx(-0.25)


def test_period_and_duty_change_step_length():
    g = TrajectoryGenerator()
    v = np.array([0.20, 0.0, 0.0])
    a = g.generate('FL', 0.0, False, v, T_cycle=0.5, duty_factor=0.5)
    b = g.generate('FL', 0.0, False, v, T_cycle=1.0, duty_factor=0.75)
    assert b[0] > a[0]


def test_yaw_velocity_is_planar_and_foot_dependent():
    g = TrajectoryGenerator()
    v = np.array([0.0, 0.0, 0.50])
    left = g.generate('FL', 0.0, False, v)
    right = g.generate('FR', 0.0, False, v)
    assert left[0] < g.nominal_positions['FL'][0]
    assert right[0] > g.nominal_positions['FR'][0]
    assert left[2] == right[2] == pytest.approx(-0.30)


def test_stance_does_not_modify_input():
    g = TrajectoryGenerator()
    start = [0.10, 0.05, -0.30]
    out = g.generate_stance(start, np.zeros(3), 0.25, 0.5, 0.5)
    assert start == [0.10, 0.05, -0.30]
    assert out.shape == (3,)


@pytest.mark.parametrize('command', ([0.1, 0.0], [float('nan'), 0, 0]))
def test_bad_command_rejected(command):
    with pytest.raises(ValueError):
        TrajectoryGenerator().generate('FL', 0.1, False, command)
