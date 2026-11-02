"""G1 reference clock overrun arithmetic; ideal feedback is NOT physics proof."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from gait_fixture import IdealFeedback
from test_gait import machine


def shifting(model):
    plant=IdealFeedback(model);value=machine(model,plant);value.request_contact_calibration()
    for _ in range(150):
        result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if (value.phase=='SHIFT' and value._shift_plan is None
                and .2<(plant.ros-value._phase_start)/1e9/value._shift_duration<.6):
            plant.tick(value,result);return value,plant
        plant.tick(value,result)
    raise AssertionError('fixture did not reach moving G1 SHIFT')


def sample_at(bundle,ros,wall):
    return replace(bundle,**{key:replace(getattr(bundle,key),stamp_ns=ros,received_ns=wall,sequence=ros)
        for key in ('joints','imu','contacts','body','scan','carry')})


def test_g1_clock_jump_cannot_skip_more_than_one_nominal_reference_step(nav_robot_model):
    fixture=json.loads((Path(__file__).parent/'fixtures/native_a50_shift_clock_gap.json').read_text())
    first,plant=shifting(nav_robot_model);second=deepcopy(first)
    ros,wall=first._last_ros,first._last_wall
    normal=first.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),(0.,0.,0.),ros+20_000_000,wall+20_000_000)
    r,w=ros+fixture['decision_ros_gap_ns'],wall+fixture['decision_wall_gap_ns']
    delayed=second.advance(sample_at(plant.state,r,w),(0.,0.,0.),r,w)
    assert normal.state!='FAULT' and delayed.state!='FAULT'
    assert np.allclose(second.reference_body,first.reference_body,atol=1e-12), 'one delayed ROS update consumed a multi-step G1 body reference'
    assert second._phase_start==first._phase_start,'original ROS phase origin was retagged'
    assert second.calibration_snapshot()['request']['deadline_wall_ns']==first.calibration_snapshot()['request']['deadline_wall_ns']


def test_reference_clock_does_not_extend_original_g1_wall_deadline(nav_robot_model):
    value,plant=shifting(nav_robot_model)
    deadline=value.calibration_snapshot()['request']['deadline_wall_ns'];ros=value._last_ros+20_000_000
    result=value.advance(sample_at(plant.state,ros,deadline),(0.,0.,0.),ros,deadline)
    assert result.state=='FAULT' and result.reason=='calibration original wall deadline'


def test_g1_clock_pause_and_resume_never_catches_up_held_reference_steps(nav_robot_model):
    value,plant=shifting(nav_robot_model);normal=deepcopy(value)
    ros,wall=value._last_ros,value._last_wall;held=value.reference_body.copy()
    for i in (1,2):
        result=value.advance(sample_at(plant.state,ros,wall),(0.,0.,0.),ros,wall+i*20_000_000)
        assert result.state!='FAULT'
        assert np.array_equal(value.reference_body,held)
    result=value.advance(sample_at(plant.state,ros+78_000_000,wall+60_000_000),(0.,0.,0.),ros+78_000_000,wall+60_000_000)
    baseline=normal.advance(sample_at(plant.state,ros+20_000_000,wall+20_000_000),(0.,0.,0.),ros+20_000_000,wall+20_000_000)
    assert result.state!='FAULT' and baseline.state!='FAULT'
    assert np.allclose(value.reference_body,normal.reference_body,atol=1e-12)


def test_nominal_crawl_retains_its_original_ros_parameterized_shift_curve(nav_robot_model):
    from test_calibration_planning_budget import prepared
    from integrated_robot_navigation.gait import blend
    plant=IdealFeedback(nav_robot_model);value=prepared(nav_robot_model,plant,False)
    list(value._shift_plan);value._shift_plan=None
    r,w=plant.ros+20_000_000,plant.wall+20_000_000
    result=value.advance(sample_at(plant.state,r,w),(.001,0.,0.),r,w)
    assert result.state!='FAULT',result.reason
    weight=blend((r-value._phase_start)/1e9/value._shift_duration)
    assert np.allclose(value.offset,value._offset_start*(1-weight)+value._offset_goal*weight,atol=1e-12)
    assert value._calibration_shift_clock is None
