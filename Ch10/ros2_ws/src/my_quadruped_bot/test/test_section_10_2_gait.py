"""Pure NumPy gait-scheduler contract tests (no ROS runtime required)."""
import math
import pytest
from my_quadruped_bot.gait_planner import GaitPlanner


def test_trot_diagonal_states():
    p = GaitPlanner('trot')
    states = p.get_leg_states()
    assert states['FL'] == states['RR']
    assert states['FR'] == states['RL']
    assert states['FL'][1] is False
    assert states['FR'][1] is True


def test_large_dt_wrap_and_boundary():
    p = GaitPlanner('trot', cycle_time=0.5)
    p.update(1.125)
    assert math.isclose(p.current_time, 0.125, abs_tol=1e-12)
    s = p.get_leg_states()
    assert math.isclose(s['FL'][0], 0.5)


@pytest.mark.parametrize('dt', (-0.1, float('nan'), float('inf')))
def test_invalid_dt_rejected(dt):
    p = GaitPlanner()
    with pytest.raises(ValueError):
        p.update(dt)


@pytest.mark.parametrize('period', (0.0, -0.2, float('nan')))
def test_invalid_period_rejected(period):
    with pytest.raises(ValueError):
        GaitPlanner(cycle_time=period)


def test_invalid_gait_rejected():
    with pytest.raises(ValueError):
        GaitPlanner(gait_type='unknown')
