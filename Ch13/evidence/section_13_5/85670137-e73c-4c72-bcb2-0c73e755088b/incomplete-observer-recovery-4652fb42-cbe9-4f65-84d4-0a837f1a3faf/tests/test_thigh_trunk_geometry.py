"""Conservative URDF cylinder enclosure matches the native capsule witness."""
import json
from pathlib import Path
import numpy as np
import pytest
import mujoco
from integrated_robot_navigation import leg_kinematics as legs
from integrated_robot_navigation.geometry import navigation_mjcf


def test_measured_native_rr_collision_is_rejected_without_changing_joint_limits(nav_robot_model):
    row=json.loads(Path(__file__).with_name('native_982b_collision.json').read_text())
    assert hasattr(legs,'thigh_trunk_clearance'),'runtime URDF clearance predicate missing'
    q=tuple(row['joints']['rr_'+p+'_joint'] for p in ('hip','thigh','calf'))
    assert legs.thigh_trunk_clearance(nav_robot_model,'rr_foot',q)<0.
    assert legs.thigh_trunk_clearance(nav_robot_model,'rr_foot',(0.,-.5,1.))>.005


@pytest.mark.parametrize('foot',['fr_foot','fl_foot','rr_foot','rl_foot'])
def test_analytic_capsule_clearance_matches_native_geometry_across_rolls(nav_robot_model,foot):
    assert hasattr(legs,'thigh_trunk_clearance'),'runtime URDF clearance predicate missing'
    native=mujoco.MjModel.from_xml_string(navigation_mjcf(nav_robot_model));data=mujoco.MjData(native)
    trunk=native.geom('base_collision').id
    thigh=next(g for g in range(native.ngeom) if native.geom_bodyid[g]==native.body(foot[:2]+'_thigh_link').id)
    for roll in np.linspace(-.2,.2,9):
        q=(roll,-.5,1.)
        for part,value in zip(('hip','thigh','calf'),q):
            data.qpos[native.jnt_qposadr[native.joint(foot[:2]+'_'+part+'_joint').id]]=value
        mujoco.mj_forward(native,data)
        expected=mujoco.mj_geomDistance(native,data,trunk,thigh,.1,None)
        # Penetration depths may use engine-specific contact algorithms; sign
        # and all separated distances must agree without increasing clearance.
        actual=legs.thigh_trunk_clearance(nav_robot_model,foot,q)
        assert (actual>=0)==(expected>=0)
        if expected>=0:assert actual==pytest.approx(expected,abs=1e-7)
