"""Bounded owner observation must neither grant motion nor change the kernel."""
from copy import deepcopy
import numpy as np
import pytest
from test_crawl_shift_clock_progress import shifting
from test_calibration_clock_progress import sample_at


@pytest.mark.parametrize('permit',[True,False])
def test_model_stage_observer_preserves_shift_result_and_credit(nav_robot_model,permit):
    plain,plant=shifting(nav_robot_model,(.01,0.,0.))
    traced=deepcopy(plain);seen=[]
    traced.set_stage_observer(seen.append)
    ros,wall=plain._last_ros+20_000_000,plain._last_wall+20_000_000
    state=sample_at(plant.state,ros,wall)
    expected=plain.advance(state,(.01,0.,0.),ros,wall,reference_permitted=permit)
    actual=traced.advance(state,(.01,0.,0.),ros,wall,reference_permitted=permit)
    assert actual==expected
    assert np.array_equal(traced.reference_body,plain.reference_body)
    assert traced._crawl_shift_clock==plain._crawl_shift_clock
    assert seen[:4]==['model_validate','model_fk','model_mass','model_safety']
    if permit:
        assert seen[4:]==['model_reference','model_solve']
    else:
        assert len(seen)==4 and actual.joint_targets is None


def test_expired_measurement_still_faults_before_any_fk_or_solve(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.));seen=[]
    value.set_stage_observer(seen.append)
    # Fresh dispatch clocks, deliberately stale original measurement.
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    state=sample_at(plant.state,ros-200_000_001,wall-200_000_001)
    result=value.advance(state,(.01,0.,0.),ros,wall)
    assert result.state=='FAULT' and 'age' in result.reason
    assert result.joint_targets is None and not seen
