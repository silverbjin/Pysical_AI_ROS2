"""Book policy changes waiting time, never measured safety or recovery."""
import math
import pytest
from integrated_robot_navigation.carry_profile import default_limits, _validate_limits
from gait_fixture import IdealFeedback
from test_gait import machine


def test_book_default_has_bounded_twenty_second_calibration_lease():
    limits=default_limits()
    assert limits.get('calibration_wall_timeout_s')==20., 'book startup need not meet a hard10wall second target'


def test_explicit_calibration_request_uses_book_lease(nav_robot_model):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    value.request_contact_calibration(ros_ns=plant.ros,wall_ns=plant.wall)
    request=value.calibration_snapshot()['request']
    assert request['deadline_wall_ns']-request['wall_ns']==20_000_000_000


def test_deferred_calibration_request_uses_same_lease(nav_robot_model):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    value.request_contact_calibration()
    result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
    assert result.state!='FAULT',result.reason
    request=value.calibration_snapshot()['request']
    assert request['deadline_wall_ns']-request['wall_ns']==20_000_000_000


@pytest.mark.parametrize('value',[True,0.,9.,20.1,math.inf,math.nan,'20'])
def test_calibration_wait_cannot_be_disabled_or_unbounded(value):
    limits=default_limits();limits['calibration_wall_timeout_s']=value
    with pytest.raises(ValueError,match='calibration_wall_timeout_s'):_validate_limits(limits)


def test_explicit_ten_second_diagnostic_profile_remains_available(nav_robot_model):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    value.limits['calibration_wall_timeout_s']=10.
    value.request_contact_calibration(ros_ns=plant.ros,wall_ns=plant.wall)
    request=value.calibration_snapshot()['request']
    assert request['deadline_wall_ns']-request['wall_ns']==10_000_000_000
