"""Balanced body-relative stance, not accumulated previous world endpoints.

These reference/IK tests are not native gait acceptance. The travel budgets
are integrated phase time, not a claim that a physical crawl cycle takes 8s.
"""
import json
from pathlib import Path
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from test_gait import machine


@pytest.mark.parametrize('vx',[.01,-.01])
def test_first_swing_centers_the_next_stance_instead_of_advancing_a_full_stride(nav_robot_model,vx):
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    nominal={key:(np.linalg.inv(value.travel)@np.r_[point,1.])[:3]
        for key,point in value._targets.items()}
    for _ in range(1000):
        result=value.advance(plant.state,(vx,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        if result.phase=='SWING':break
        plant.tick(value,result)
    else:pytest.fail('no normal swing reached')
    foot=result.swing_foot
    neutral=(value.travel@np.r_[nominal[foot],1.])[:2]
    # Remaining swing plus half the next stance centers the workspace. A full
    # old-anchor stride adds a startup/command-change bias and is not centered.
    # Body travel is intermittent: only SHIFT contributes. The old cycle_s
    # bound still conservatively limits commands; it is not executed travel.
    horizon=(len(value.ORDER)*sum(value.TRAVEL_BUDGET.values())+value.TRAVEL_BUDGET['SWING'])/2
    assert np.allclose(value._swing_goal[:2]-neutral,[vx*horizon,0.],atol=1e-9), \
        'foot endpoint retains the full previous-anchor stride rather than a centered stance'
    assert np.linalg.norm(value._swing_goal[:2]-value._swing_start[:2])<=value.limits['max_foot_displacement_m']


def test_native_failed_endpoint_stays_rejected_and_a_centered_short_step_is_feasible(nav_robot_model):
    row=json.loads(Path(__file__).with_name('native_3127_workspace.json').read_text())
    plant=IdealFeedback(nav_robot_model);value=machine(nav_robot_model,plant)
    value.reference_body=np.array(row['reference_body'])
    value._targets={name:np.array(point) for name,point in row['targets'].items()}
    with pytest.raises(ValueError,match='ik footprint joint bound'):
        value._solve(row['joints'],True)
    # Original trace did not record travel separately. This deliberately chosen
    # command frame checks feasibility, not a reconstructed native trajectory.
    value.travel=value.reference_body.copy()
    before=value._targets['fl_foot'].copy()
    value._targets['fl_foot'][:2]=value._centered_swing_goal('fl_foot',.01,0.)
    assert np.linalg.norm(value._targets['fl_foot']-before)<=value.limits['max_foot_displacement_m']
    angles=value._solve(row['joints'],True)
    assert .8<=angles['fl_calf_joint']<=1.4
