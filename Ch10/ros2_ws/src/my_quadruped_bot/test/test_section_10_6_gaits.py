"""Gait transitions must be instance-local and survive long update intervals."""
import pytest
from my_quadruped_bot.generalized_gait_planner import GeneralizedGaitPlanner, GAIT_LIBRARY


def test_large_dt_and_transition():
    p = GeneralizedGaitPlanner()
    assert p.set_gait('crawl') is True
    p.update(1.03)
    assert p.is_cycle_completed()
    assert p.current_gait.name == 'crawl'
    assert 0 <= p.current_time < 1 / p.current_gait.frequency


def test_each_planner_owns_its_config():
    a = GeneralizedGaitPlanner()
    b = GeneralizedGaitPlanner()
    a.current_gait.frequency = 4.0
    assert b.current_gait.frequency == 2.0
    assert GAIT_LIBRARY['trot'].frequency == 2.0


def test_unknown_gait_and_negative_dt():
    p = GeneralizedGaitPlanner()
    assert p.set_gait('wrong') is False
    with pytest.raises(ValueError):
        p.update(-0.01)


def test_crawl_stance_fraction():
    p = GeneralizedGaitPlanner('crawl')
    assert p.current_gait.duty_factor == 0.75
    assert len(p.get_leg_states()) == 4
