"""Waiting for application freezes references, never the original safety checks."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from test_crawl_shift_clock_progress import shifting
from test_calibration_clock_progress import sample_at
from gait_fixture import IdealFeedback
from test_gait import machine


@pytest.mark.parametrize('phase',['SHIFT','SWING'])
def test_application_wait_observes_safety_without_recomputing_unpublishable_ik(phase,nav_robot_model,monkeypatch):
    value,plant=(shifting(nav_robot_model,(.01,0.,0.)) if phase=='SHIFT' else swinging(nav_robot_model))
    held=value.reference_body.copy();targets=deepcopy(value._targets)
    solves=[];original=value._solve
    def observe(*args,**kwargs):
        solves.append(True)
        return original(*args,**kwargs)
    monkeypatch.setattr(value,'_solve',observe)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    result=value.advance(sample_at(plant.state,ros,wall),(.01,0.,0.),ros,wall,reference_permitted=False)
    assert result.state=='CRAWL'
    assert not solves, 'waiting for the previous application recomputed IK for a command that cannot be published'
    assert result.joint_targets is None
    assert np.array_equal(value.reference_body,held)
    assert all(np.array_equal(value._targets[key],point) for key,point in targets.items())
    assert (value._last_ros,value._last_wall)==(ros,wall), 'safety observation was skipped with IK'


def test_no_credit_holds_shift_reference_but_consumes_original_decision_clocks(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    held=value.reference_body.copy();targets=deepcopy(value._targets)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    result=value.advance(sample_at(plant.state,ros,wall),(.01,0.,0.),ros,wall,
        reference_permitted=False)
    assert result.state=='CRAWL'
    assert np.array_equal(value.reference_body,held)
    assert all(np.array_equal(value._targets[key],point) for key,point in targets.items())
    assert value._last_ros==ros and value._last_wall==wall


def test_no_credit_cannot_bypass_measured_support_failure(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.))
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    bundle=sample_at(plant.state,ros,wall)
    data={**bundle.contacts.data,'forces':(0.,0.,30.,30.),'touching':(False,False,True,True)}
    bundle=replace(bundle,contacts=replace(bundle.contacts,data=data))
    result=value.advance(bundle,(.01,0.,0.),ros,wall,reference_permitted=False)
    assert result.state=='FAULT' and result.joint_targets is None


def test_confirmed_reference_advances_one_bounded_step_after_a_short_post_wait_tick(nav_robot_model):
    normal,plant=shifting(nav_robot_model,(.01,0.,0.));delayed=deepcopy(normal)
    ros,wall=normal._last_ros,normal._last_wall
    expected=normal.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),
        (.01,0.,0.),ros+20_000_000,wall+20_000_000)
    waiting=delayed.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),
        (.01,0.,0.),ros+20_000_000,wall+20_000_000,reference_permitted=False)
    assert waiting.state=='CRAWL'
    # Application was confirmed before this next short scheduling interval.
    actual=delayed.advance(sample_at(plant.state,ros+30_000_000,wall+30_000_000),
        (.01,0.,0.),ros+30_000_000,wall+30_000_000,reference_permitted=True)
    assert expected.state=='CRAWL' and actual.state=='CRAWL'
    assert np.allclose(delayed.reference_body,normal.reference_body,atol=1e-12), \
        'waiting decision consumed part of the next single permitted reference step'
    assert delayed._last_ros==ros+30_000_000 and delayed._last_wall==wall+30_000_000


def test_confirmation_after_multiple_waits_cannot_bank_or_catch_up_multiple_reference_steps(nav_robot_model):
    normal,plant=shifting(nav_robot_model,(.01,0.,0.));delayed=deepcopy(normal)
    ros,wall=normal._last_ros,normal._last_wall
    normal.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),
        (.01,0.,0.),ros+20_000_000,wall+20_000_000)
    for delta in (20_000_000,40_000_000,60_000_000):
        delayed.advance(sample_at(plant.state,ros+delta,wall+delta),(.01,0.,0.),
            ros+delta,wall+delta,reference_permitted=False)
    result=delayed.advance(sample_at(plant.state,ros+70_000_000,wall+70_000_000),
        (.01,0.,0.),ros+70_000_000,wall+70_000_000,reference_permitted=True)
    assert result.state=='CRAWL'
    assert np.allclose(delayed.reference_body,normal.reference_body,atol=1e-12), \
        'confirmed application caught up several missed reference periods'


def test_wall_due_does_not_extrapolate_18ms_original_ros_into_20ms_trajectory(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.));same=deepcopy(value);longer=deepcopy(value)
    ros,wall=value._last_ros,value._last_wall
    for owner,dr,dw in ((value,18_000_000,20_000_000),(same,18_000_000,18_000_000),
                        (longer,20_000_000,20_000_000)):
        result=owner.advance(sample_at(plant.state,ros+dr,wall+dw),(.01,0.,0.),ros+dr,wall+dw)
        assert result.state=='CRAWL'
    assert np.allclose(value.reference_body,same.reference_body,atol=1e-12)
    assert not np.allclose(value.reference_body,longer.reference_body,atol=1e-12), \
        'wall cadence replaced original ROS progress with a synthesized 20ms step'


def test_explicit_stop_does_not_wait_for_reference_credit(nav_robot_model):
    value,plant=shifting(nav_robot_model,(.01,0.,0.));value.request_stop(urgent=True)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    result=value.advance(sample_at(plant.state,ros,wall),(0.,0.,0.),ros,wall,reference_permitted=False)
    assert result.state!='CRAWL' and value.stopping


def swinging(model):
    plant=IdealFeedback(model);value=machine(model,plant)
    for _ in range(1200):
        result=value.advance(plant.state,(.01,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if value.phase=='SWING' and .3<(plant.ros-value._phase_start)/1e9/value._swing_duration<.6:
            return value,plant
    raise AssertionError('moving SWING not reached')


def test_delayed_swing_cannot_catch_up_missed_reference_steps(nav_robot_model):
    normal,plant=swinging(nav_robot_model);delayed=deepcopy(normal)
    ros,wall=normal._last_ros,normal._last_wall
    a=normal.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),(.01,0.,0.),
        ros+20_000_000,wall+20_000_000,reference_permitted=True)
    b=delayed.advance(sample_at(plant.state,ros+40_000_000,wall+27_906_419),(.01,0.,0.),
        ros+40_000_000,wall+27_906_419,reference_permitted=True)
    assert a.state!='FAULT' and b.state!='FAULT'
    assert all(np.allclose(delayed._targets[key],point,atol=1e-12)
        for key,point in normal._targets.items())


def test_waiting_credit_keeps_three_stance_margin_even_after_early_foot_contact(nav_robot_model):
    value,plant=swinging(nav_robot_model)
    ros,wall=value._last_ros+20_000_000,value._last_wall+20_000_000
    bundle=sample_at(plant.state,ros,wall)
    _,_,_,_,_,com=value._measure(bundle,ros,wall)
    points=tuple((com[0]+x,com[1]+y,0.) for x,y in ((-.2,-.1),(.2,-.1),(.2,.1),(-.2,.1)))
    data={**bundle.contacts.data,'points':points,'forces':(30.,)*4,'touching':(True,)*4}
    bundle=replace(bundle,contacts=replace(bundle.contacts,data=data))
    _,_,_,loads,actual_points,actual_com=value._measure(bundle,ros,wall)
    assert value._margin(actual_com,loads,actual_points)>.09
    assert value._margin(actual_com,loads,actual_points,value.swing_foot)<.01
    result=value.advance(bundle,(.01,0.,0.),ros,wall,reference_permitted=False)
    assert result.state=='FAULT' and result.reason=='swing support lost', \
        'application wait bypassed the original three-stance SWING support check'


def test_unload_search_keeps_original_bounded_rate_across_confirmed_application_wait(nav_robot_model):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    for _ in range(500):
        result=value.advance(plant.state,(.01,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if value.phase=='SHIFT' and value._unload_start is not None:break
    else:raise AssertionError('measured unload not reached')
    foot=value.ORDER[value._index];initial=value._targets[foot][2]
    ros,wall=value._last_ros,value._last_wall
    for index,permitted in ((1,False),(2,False),(3,True)):
        r,w=ros+index*20_000_000,wall+index*20_000_000
        result=value.advance(sample_at(plant.state,r,w),(.01,0.,0.),r,w,
            reference_permitted=permitted)
        assert result.state!='FAULT',result.reason
        if not permitted:assert value._targets[foot][2]==initial
    assert abs(value._targets[foot][2]-initial-value.limits['unload_speed_mps']*.06)<1e-12, \
        'reference-curve clock incorrectly slowed the separate actual-time contact search'


def test_touchdown_search_uses_original_bounded_rate_without_extending_its_deadline(nav_robot_model):
    value,plant=swinging(nav_robot_model);foot=value.swing_foot
    value.phase='TOUCHDOWN';value._phase_start=value._last_ros
    value._targets[foot][2]=value.floor[foot]+.0005
    initial=value._targets[foot][2];ros,wall=value._last_ros,value._last_wall
    for index,permitted in ((1,False),(2,False),(3,True)):
        r,w=ros+index*20_000_000,wall+index*20_000_000
        result=value.advance(sample_at(plant.state,r,w),(.01,0.,0.),r,w,
            reference_permitted=permitted)
        assert result.state!='FAULT',result.reason
    assert abs(value._targets[foot][2]-initial+value.limits['unload_speed_mps']*.06)<1e-12
    r,w=ros+1_000_000_001,wall+1_000_000_001
    value._last_ros=r-20_000_000;value._last_wall=w-20_000_000
    result=value.advance(sample_at(plant.state,r,w),(.01,0.,0.),r,w,reference_permitted=False)
    assert result.state=='FAULT' and result.reason=='touchdown timeout'
