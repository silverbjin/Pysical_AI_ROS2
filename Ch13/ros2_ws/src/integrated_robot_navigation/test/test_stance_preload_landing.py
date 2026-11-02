"""A completed step must retain its held servo preload, not encoder height.

Synthetic ideal feedback isolates reference continuity under an explicit encoder
load offset. It is neither compliant physics nor native G2 success evidence.
"""
from dataclasses import replace
import numpy as np
import pytest

from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.gait import CrawlMachine
from gait_fixture import IdealFeedback
from test_landing_continuity import contact


def preloaded_swing(model):
    plant=IdealFeedback(model)
    held={name:plant.state.joints.data['position'][name] for name in model.joint_names}
    measured=dict(plant.state.joints.data['position'])
    for foot in model.feet:measured[foot[:2]+'_calf_joint']+=.025
    plant.state=replace(plant.state,joints=replace(plant.state.joints,
        data={**plant.state.joints.data,'position':measured}))
    machine=CrawlMachine(model,default_limits())
    machine.reset(plant.state,plant.ros,plant.wall,held_targets=held)
    original={foot:float(point[2]) for foot,point in machine._targets.items()}
    assert all(machine.floor[f]-original[f]>.002 for f in model.feet)
    plant.floor_center=max(machine.floor.values())
    for _ in range(650):
        result=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if result.phase=='SWING' and (plant.ros-machine._phase_start)/1e9>=.7*machine._swing_duration:
            return plant,machine,result,original
        plant.tick(machine,result)
    pytest.fail('preloaded reference fixture never reached a descending swing')


def test_planned_landing_and_completed_reference_preserve_held_preload(nav_robot_model):
    plant,machine,previous,original=preloaded_swing(nav_robot_model)
    foot='fl_foot'
    assert machine._swing_goal[2]==pytest.approx(original[foot],abs=1e-12), \
        'measured floor replaced the held support preload at the planned endpoint'
    before=machine._targets[foot].copy()
    for _ in range(500):
        plant.tick(machine,previous)
        previous=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
        assert previous.state!='FAULT',previous.reason
        point=machine._targets[foot].copy()
        assert np.linalg.norm(point-before)<=.020000001*.02
        before=point
        if previous.phase=='SETTLE':
            assert point[2]==pytest.approx(original[foot],abs=1e-12)
            assert machine.floor[foot]>point[2]+.002
            return
    pytest.fail('planned preload endpoint never reached measured landing')


def test_contact_search_never_raises_a_preloaded_reference_to_the_measured_floor(nav_robot_model):
    plant,machine,previous,original=preloaded_swing(nav_robot_model)
    foot='fl_foot'
    machine._targets[foot][2]=original[foot]
    machine.phase='TOUCHDOWN';machine._phase_start=plant.ros
    plant.tick(follow=False);contact(plant,False)
    result=machine.advance(plant.state,(.0001,0.,0.),plant.ros,plant.wall)
    assert result.state!='FAULT',result.reason
    assert 0<=original[foot]-machine._targets[foot][2]<=.002*.02+1e-12, \
        'the measured-floor clamp made a new upward reference step'
