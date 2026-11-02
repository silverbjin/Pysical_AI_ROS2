"""Batch bounded G1 arithmetic, never change its physical reference curve."""
import numpy as np
from gait_fixture import IdealFeedback
from test_gait import machine


def prepared(model,plant,calibrating):
    value=machine(model,plant)
    if calibrating:value.request_contact_calibration()
    value.state='CALIBRATING' if calibrating else 'CRAWL'
    q,_,_,loads,points,com=value._measure(plant.state,plant.ros,plant.wall)
    value._begin_shift(com,loads,points,plant.ros,q)
    return value


def test_g1_batches_four_predictions_while_normal_walk_remains_one(nav_robot_model):
    for calibrating,expected in ((True,4),(False,1)):
        plant=IdealFeedback(nav_robot_model);value=prepared(nav_robot_model,plant,calibrating)
        original=value._shift_plan;steps=[]
        def counted():
            for step in original:
                steps.append(None)
                yield step
        value._shift_plan=counted()
        held={n:p.copy() for n,p in value._targets.items()}
        result=value.advance(plant.state,(0.,0.,0.) if calibrating else (.001,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        assert len(steps)==expected,'G1 planning still waits a full20ms between every arithmetic candidate'
        assert value._shift_plan is not None
        assert all(np.allclose(value._targets[n],p,atol=1e-12) for n,p in held.items())


def test_batched_g1_retains_identical_goal_duration_and_starts_curve_only_after_planning(nav_robot_model):
    plant=IdealFeedback(nav_robot_model)
    expected=prepared(nav_robot_model,plant,True);list(expected._shift_plan)
    actual=prepared(nav_robot_model,plant,True)
    for _ in range(20):
        result=actual.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if actual._shift_plan is None:
            assert actual._phase_start==plant.ros
            break
        assert np.array_equal(actual.offset,actual._offset_start)
        plant.tick(actual,result)
    else:raise AssertionError('bounded G1 planner never completed')
    assert np.array_equal(actual._offset_goal,expected._offset_goal)
    assert actual._shift_duration==expected._shift_duration
    assert actual._shift_accel_budget==expected._shift_accel_budget==.1
