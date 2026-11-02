"""A safe nominal pose must also permit its owned unload/stance references.

Closed native geometry, with fixed future XY for a no-travel replan. This
validates reference feasibility, never measured support or physical success.
"""
import json
from pathlib import Path
import numpy as np
from gait_fixture import IdealFeedback
from test_stance_load_transfer import helper
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.leg_kinematics import fk_leg,ik_leg,thigh_trunk_clearance
from integrated_robot_navigation.projection import body_rotation
from integrated_robot_navigation.support import center_of_mass,support_margin


def test_constrained_fallback_reserves_unload_and_stance_height_volume(nav_robot_model):
    row=json.loads((Path(__file__).parent/'fixtures/native_b82a_reference_envelope.json').read_text())
    model=helper(nav_robot_model).model;limits=default_limits();plant=IdealFeedback(model)
    m=CrawlMachine(model,limits,load_transfer_policy='stance_admittance')
    m.reset(plant.state,plant.ros,plant.wall);assert m.state!='FAULT'
    m.state='CRAWL';m.reference_body=np.array(row['reference_body']);m.travel=m.reference_body.copy()
    m._index=m.ORDER.index(row['swing_foot']);inverse=np.linalg.inv(m.travel)
    m._targets={}
    for foot in model.feet:
        names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
        local=fk_leg(model,foot,tuple(row['held_joint_targets'][n] for n in names))
        m._targets[foot]=(m.reference_body@np.r_[local,1.])[:3]
    m._nominal_feet={f:(inverse@np.r_[p,1.])[:3] for f,p in m._targets.items()}
    m._stance_reference_z=dict(row['stance_reference_z']);m._stance_origin_z=dict(row['stance_reference_z'])
    m.floor=dict(row['floor']);q=row['joints']['position'];pose=np.eye(4)
    pose[:3,:3]=body_rotation(row['body'])[0];pose[:3,3]=row['body']['position']
    com=np.array(center_of_mass(model,q,pose));points=dict(zip(row['contacts']['names'],row['contacts']['points']))
    initial=m.reference_body.copy();previous=dict(q);previous.update(m._solve(q,True,initial))
    baseline=np.array(center_of_mass(model,previous,initial))
    m._begin_shift(com,{f:True for f in model.feet},points,plant.ros,q)
    for _ in m._shift_plan:pass
    goal=initial.copy();goal[:2,3]+=m._offset_goal-m._offset_start;inverse=np.linalg.inv(goal)
    planned=dict(q);planned.update(m._solve(q,True,goal))
    new_com=com+np.array(center_of_mass(model,planned,goal))-baseline
    assert support_margin(new_com,[points[f] for f in model.feet if f!=row['swing_foot']])>=.025-1e-12
    p=np.array([points[f] for f in model.feet]);_,_,vh=np.linalg.svd(np.column_stack((np.ones(4),p[:,1],-p[:,0])).T)
    null=vh[-1];selected=model.feet.index(row['swing_foot'])
    for i,foot in enumerate(model.feet):
        origin=m._stance_origin_z[foot]
        if i==selected:
            lo=min(m.floor[foot],m._stance_reference_z[foot])-.002
            hi=max(m.floor[foot]+limits['swing_height_m'],origin+limits['max_unload_height_m'])
        else:
            edge=origin+np.sign(null[i]/null[selected])*limits['max_unload_height_m']
            lo=min(origin,edge,m._targets[foot][2]);hi=max(origin,edge,m._targets[foot][2])
        names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
        for z in (lo,(lo+hi)/2,hi):
            target=m._targets[foot].copy();target[2]=z
            angles=ik_leg(model,foot,(inverse@np.r_[target,1.])[:3],tuple(q[n] for n in names))
            clearance=thigh_trunk_clearance(model,foot,angles)
            assert clearance>=.0001,(foot,z,clearance)
            assert all(limits['gait_joint_bounds'][p][0]<=v<=limits['gait_joint_bounds'][p][1]
                for p,v in zip(('hip','thigh','calf'),angles)),(foot,z,angles)
