"""Native failed geometry: minimum safe inset is not balanced support loading.

URDF/IK arithmetic only. No simulated or measured force is synthesized here.
"""
import json
from pathlib import Path
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.support import center_of_mass,support_margin
from test_stance_load_transfer import helper


def planned(model,policy,*,calibrating=False):
    row=json.loads((Path(__file__).parent/'fixtures/native_15382_support_balance.json').read_text())
    model=helper(model).model
    value=CrawlMachine(model,default_limits(),load_transfer_policy=policy)
    plant=IdealFeedback(model)
    value.reset(plant.state,plant.ros,plant.wall)
    assert value.state!='FAULT',value.reason
    value.state='CRAWL';value.calibrating=calibrating
    value.reference_body=np.array(row['reference_body'])
    value._targets={f:np.array(p) for f,p in row['targets'].items()}
    value._stance_reference_z=dict(row['stance_reference_z'])
    value._index=value.ORDER.index(row['swing_foot'])
    # This is a no-travel replan of the closed geometry, not replay of an
    # unrecorded live travel accumulator. At zero requested velocity retain
    # the current foot XY for the future landing, not the unit plant's origin.
    value.travel=value.reference_body.copy()
    inverse=np.linalg.inv(value.travel)
    value._nominal_feet={f:(inverse@np.r_[p,1.])[:3] for f,p in value._targets.items()}
    q=row['joints']['position'];pose=np.eye(4)
    pose[:3,:3]=body_rotation(row['body'])[0];pose[:3,3]=row['body']['position']
    com=np.array(center_of_mass(model,q,pose));points=dict(zip(row['contacts']['names'],row['contacts']['points']))
    loads={f:True for f in model.feet}
    initial=value.reference_body.copy()
    old=dict(q);old.update(value._solve(q,True,initial))
    baseline=np.array(center_of_mass(model,old,initial))
    value._begin_shift(com,loads,points,0,q)
    for _ in value._shift_plan:pass
    goal=initial.copy();goal[:2,3]+=value._offset_goal-value._offset_start
    predicted=dict(q);predicted.update(value._solve(q,True,goal))
    predicted_com=com+np.array(center_of_mass(model,predicted,goal))-baseline
    support=np.array([points[f] for f in model.feet if f!=row['swing_foot']])
    fractions=np.linalg.solve(np.vstack((support[:,:2].T,np.ones(3))),np.r_[predicted_com[:2],1.])
    return value,fractions,support_margin(predicted_com,support)


def test_explicit_force_profile_does_not_stop_at_first_geometric_inset(nav_robot_model):
    value,fractions,margin=planned(nav_robot_model,'stance_admittance')
    assert margin>=.025-1e-12
    # Independent vertical force and moment equilibrium: the old nearest
    # inset puts about half the load on the already saturated FL leg. A
    # collision-clear candidate in this fixed fixture reduces the peak <43%.
    assert max(fractions)<.43,dict(fractions=fractions,plan=value.load_balance_plan)
    assert sum(fractions)==pytest.approx(1.) and min(fractions)>0.
    assert value.load_balance_plan['scope']=='quasistatic_vertical_prediction_not_measured_force'


def test_default_geometric_and_g1_planning_keep_their_original_goal(nav_robot_model):
    old,fractions,_=planned(nav_robot_model,'geometric')
    g1,_,_=planned(nav_robot_model,'stance_admittance',calibrating=True)
    geometric_g1,_,_=planned(nav_robot_model,'geometric',calibrating=True)
    assert max(fractions)>.47
    assert np.array_equal(g1._offset_goal,geometric_g1._offset_goal)


def test_manual_reset_does_not_rebind_a_previous_generation_load_plan(nav_robot_model):
    value,_,_=planned(nav_robot_model,'stance_admittance')
    assert value.load_balance_plan is not None
    old_generation=value.generation
    plant=IdealFeedback(value.model)
    value.reset(plant.state,plant.ros,plant.wall)
    assert value.generation==old_generation+1 and value.state!='FAULT'
    assert value.load_balance_plan is None
