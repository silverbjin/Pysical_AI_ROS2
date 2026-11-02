"""Pure environment-gate fixtures; no fake engine evidence or clock changes."""
import importlib.util
import importlib
import pytest


def gate():
    assert importlib.util.find_spec('integrated_robot_navigation.clock_preflight'), \
        'read-only system-clock preflight missing'
    return importlib.import_module('integrated_robot_navigation.clock_preflight').ClockStabilityGate()


def test_quiet_observed_time_is_required_before_ready():
    value=gate();value.observe(0,1_000_000_000)
    assert value.observe(39_999_999_999,40_999_999_999)['state']=='WAITING'
    assert value.observe(40_000_000_000,41_000_000_000)['state']=='READY'


def test_reproduced_early_and_late_system_steps_reset_quiet_window():
    value=gate();offset=1_000_000_000;value.observe(0,offset)
    for wall,jump in [(23,-2_250_000_000),(24,2_250_000_000),
                      (31,-2_250_000_000),(32,2_250_000_000),
                      (39,-2_300_000_000),(40,2_300_000_000),(72,2_200_000_000)]:
        offset+=jump
        assert value.observe(wall*1_000_000_000,wall*1_000_000_000+offset)['state']=='WAITING'
    assert value.observe(111_999_999_999,111_999_999_999+offset)['state']=='WAITING'
    assert value.observe(112_000_000_000,112_000_000_000+offset)['state']=='READY'


def test_unstable_deadline_is_sticky_and_is_not_permission_to_retry():
    value=gate();value.observe(0,10_000_000_000)
    for second in range(30,151,30):
        result=value.observe(second*1_000_000_000,(second+10+second//30)*1_000_000_000)
    assert result['state']=='FAULT' and 'deadline' in result['reason']
    assert value.observe(200_000_000_000,215_000_000_000)['state']=='FAULT'


def test_monotonic_rollback_cannot_become_a_quiet_window():
    value=gate();value.observe(100,1000)
    assert value.observe(99,999)['state']=='FAULT'
    assert value.observe(100_000_000_000,100_000_000_900)['state']=='FAULT'
