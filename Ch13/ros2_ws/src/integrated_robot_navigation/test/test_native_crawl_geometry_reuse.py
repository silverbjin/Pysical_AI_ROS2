"""Reuse identical native geometry in the explicit crawl owner; no new cache."""
import json,time
from pathlib import Path
import numpy as np
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.native_mass import NativeMassEvaluator

def configured():
    c=json.loads((Path(__file__).parent/'fixtures/native_da61_contact_age.json').read_bytes())
    model=compile_model(c['urdf']);mass=NativeMassEvaluator(model)
    m=CrawlMachine(model,c['limits'],mass_evaluator=mass,load_transfer_policy='coupled_contact',
        async_load_transfer=True,load_result_timing='same_cycle',load_receipt_mode='event_receiver')
    m.reference_body=np.array(c['body']);m._targets={f:np.array(p) for f,p in c['targets'].items()}
    m._stance_reference_z={f:p[2] for f,p in c['targets'].items()};m.state='CRAWL';m.travel=np.eye(4)
    m.planning_reference_envelope=c['envelope'];m._planning_contact_points=c['points']
    m._index=0;m._nominal_feet={f:p.copy() for f,p in m._targets.items()}
    return c,model,m,mass

def test_current_crawl_ik_reuses_owned_native_geometry_without_python_collision_repeat(monkeypatch):
    import integrated_robot_navigation.gait as gait
    c,model,m,mass=configured();old=CrawlMachine(model,c['limits'])
    old.reference_body=m.reference_body.copy();old._targets=m._targets;old.state='CRAWL'
    try:
        expected=old._solve(c['joints'],True)
        assert m._kinematics_evaluator is m._reference_geometry
        def forbidden(*args,**kwargs):raise AssertionError('duplicated Python collision arithmetic')
        monkeypatch.setattr(gait,'thigh_trunk_clearance',forbidden)
        actual=m._solve(c['joints'],True)
        np.testing.assert_allclose([actual[n] for n in model.joint_names],[expected[n] for n in model.joint_names],atol=2e-12,rtol=0.)
    finally:m.close_load_transfer();mass.close()

def test_shift_planner_reuses_same_fresh28_sample_geometry(monkeypatch):
    import integrated_robot_navigation.reference_envelope as envelope
    c,model,m,mass=configured();calls=[];original=m._reference_geometry.evaluate
    def observed(**kwargs):calls.append(kwargs);return original(**kwargs)
    def forbidden(*args,**kwargs):raise AssertionError('Python28sample path repeated in explicit native scope')
    monkeypatch.setattr(m._reference_geometry,'evaluate',observed);monkeypatch.setattr(envelope,'reference_constraints',forbidden)
    monkeypatch.setattr(m,'_support_actuation',lambda *a,**kw:None)
    try:
        center=mass(model,c['joints'],m.reference_body)
        support=[c['points'][f] for f in model.feet if f!=m.ORDER[0]]
        plan=m._plan_shift(np.array([-.02,-.02]),support,0.,c['joints'],m.reference_body,measured_com=center,command=(0.,0.,0.))
        next(plan);next(plan)
        assert len(calls)>=2
        assert calls[-1]['envelope']==c['envelope'] and calls[-1]['joints']==c['joints']
    finally:m.close_load_transfer();mass.close()


def test_static_support_reuses_verified_native_terms_with_same_optimum(monkeypatch):
    from integrated_robot_navigation import contact_equilibrium
    c,model,m,mass=configured()
    try:
        com=mass(model,c['joints'],m.reference_body)
        args=dict(model=model,joints=c['joints'],body_pose=m.reference_body,points=c['points'],active_feet=model.feet,com=com)
        old=contact_equilibrium.static_support(**args)
        assert old['feasible']
        def forbidden(*args,**kwargs):raise AssertionError('Python URDF contact/gravity repeated')
        monkeypatch.setattr(contact_equilibrium,'leg_terms',forbidden)
        direct=contact_equilibrium.static_support(**args,terms_evaluator=mass.contact_terms)
        via_owner=m._support_actuation(c['joints'],m.reference_body,com,c['points'],active=model.feet)
        assert direct['feasible']==old['feasible']
        assert abs(direct['torque_utilization']-old['torque_utilization'])<1e-8
        assert via_owner['feasible'] and via_owner['actuation_model']=='gazebo_discrete_equilibrium_v1'
        assert via_owner['torque_utilization']>=old['torque_utilization']-1e-8
        assert len(via_owner['actuator_command_efforts'])==20
        assert all(abs(v)<=model.limits[n][3]+1e-7 for n,v in via_owner['actuator_command_efforts'].items())
        for new in (direct,via_owner):
            assert all(abs(t)<=model.limits[n][3]+1e-7 for n,t in new['joint_torques'].items())
    finally:m.close_load_transfer();mass.close()
