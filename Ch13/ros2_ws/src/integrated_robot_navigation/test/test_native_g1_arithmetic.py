"""G1 reuses identical immutable arithmetic, retaining all caller safety gates."""
import inspect
import numpy as np
import pytest
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
from integrated_robot_navigation.leg_kinematics import fk_leg
from gait_fixture import IdealFeedback


def configured(model):
    assert 'kinematics_evaluator' in inspect.signature(CrawlMachine).parameters, \
        'G1 nominal leg IK still repeats Python geometry work in the model owner'
    limits=default_limits();geometry=NativeReferenceEnvelope(model,limits)
    return CrawlMachine(model,limits),CrawlMachine(model,limits,kinematics_evaluator=geometry),geometry


def test_random_nominal_ik_preserves_moving_bounds_and_clearance_checks(nav_robot_model):
    old,new,geometry=configured(nav_robot_model);rng=np.random.default_rng(130531)
    plant=IdealFeedback(nav_robot_model);q=plant.state.joints.data['position']
    try:
        for index in range(100):
            body=np.eye(4);angle=rng.uniform(-.2,.2);body[:2,:2]=[[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]
            body[:3,3]=rng.uniform(-.2,.2,3);targets={}
            for foot in nav_robot_model.feet:
                values=[rng.uniform(-.45,.45),rng.uniform(-1.,-.2),rng.uniform(.8,1.6)]
                targets[foot]=(body@np.r_[fk_leg(nav_robot_model,foot,values),1.])[:3]
            for m in (old,new):
                m.reference_body=body;m._targets=targets;m.state='CRAWL' if index%3 else 'STAND';m.calibrating=bool(index%2)
            moving=bool(index%2)
            try:expected=old._solve(q,moving)
            except ValueError:
                with pytest.raises(ValueError):new._solve(q,moving)
            else:
                actual=new._solve(q,moving)
                assert set(actual)==set(expected)
                assert max(abs(actual[n]-expected[n]) for n in actual)<2e-12
    finally:new.close_load_transfer()
    assert not geometry._finalize.alive


def test_unreachable_nominal_target_cannot_gain_a_command(nav_robot_model):
    old,new,geometry=configured(nav_robot_model);p=IdealFeedback(nav_robot_model);q=p.state.joints.data['position']
    targets={f:np.array([20.,0.,0.]) for f in nav_robot_model.feet}
    try:
        for m in (old,new):
            m._targets=targets
            with pytest.raises(ValueError):m._solve(q,True)
    finally:new.close_load_transfer()
    assert not geometry._finalize.alive
