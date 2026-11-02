"""Independent static force/effort contracts, not a native walking proof."""
import importlib.util
from types import SimpleNamespace
import numpy as np
import pytest
from gait_fixture import IdealFeedback
from integrated_robot_navigation.support import center_of_mass, support_margin


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.contact_equilibrium'), \
        'common 3D contact/actuation equilibrium evaluator missing'
    from integrated_robot_navigation import contact_equilibrium
    return contact_equilibrium


def inputs(model):
    plant=IdealFeedback(model);plant.tick()
    return dict(model=model,joints=plant.state.joints.data['position'],body_pose=plant.pose,
        points=dict(zip(model.feet,plant.state.contacts.data['points'])),active_feet=model.feet)


def test_com_inside_support_does_not_override_tiny_motor_limits(nav_robot_model):
    args=inputs(nav_robot_model)
    com=np.asarray(center_of_mass(nav_robot_model,args['joints'],args['body_pose']))
    assert support_margin(com,list(args['points'].values()))>0.
    result=api().static_support(**args,effort_limits={n:.001 for n in nav_robot_model.joint_names})
    assert not result['feasible'] and result['torque_utilization']>1.
    assert result['scope']=='quasistatic_point_contact_prediction_not_measured_force'


def test_spatial_solution_satisfies_independent_force_moment_and_effort_balance(nav_robot_model):
    args=inputs(nav_robot_model);result=api().static_support(**args)
    assert result['feasible'],result
    mass=sum(m for m,_ in nav_robot_model.masses.values())
    com=np.asarray(center_of_mass(nav_robot_model,args['joints'],args['body_pose']))
    forces=np.array([result['forces_world'][f] for f in nav_robot_model.feet])
    assert np.allclose(forces.sum(axis=0),[0.,0.,9.81*mass],atol=1e-7)
    moment=sum((np.cross(args['points'][f]-com,force) for f,force in zip(nav_robot_model.feet,forces)),np.zeros(3))
    assert np.linalg.norm(moment)<1e-7
    assert all(abs(result['joint_torques'][n])<=nav_robot_model.limits[n][3]+1e-7 for n in nav_robot_model.joint_names)


def test_world_yaw_changes_vectors_but_not_feasibility(nav_robot_model):
    args=inputs(nav_robot_model);before=api().static_support(**args)
    angle=.73;c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
    pose=args['body_pose'].copy();pose[:3,:3]=rotation@pose[:3,:3];pose[:3,3]=rotation@pose[:3,3]
    after=api().static_support(**{**args,'body_pose':pose,
        'points':{f:rotation@np.asarray(p) for f,p in args['points'].items()}})
    # The square friction approximation is tied to world axes, but both optima
    # here are in its interior; the physical effort score must remain the same.
    assert after['feasible']==before['feasible']
    assert after['torque_utilization']==pytest.approx(before['torque_utilization'],abs=1e-7)


def test_next_three_contacts_do_not_silently_keep_the_removed_foot(nav_robot_model):
    args=inputs(nav_robot_model);active=nav_robot_model.feet[:3]
    result=api().static_support(**{**args,'active_feet':active},min_force=0.)
    assert set(result['forces_world'])==set(active)


@pytest.mark.parametrize('status,success',[(1,False),(2,False),(0,False)])
def test_optimizer_terminal_failure_cannot_be_used_as_a_plan(nav_robot_model,monkeypatch,status,success):
    module=api()
    monkeypatch.setattr(module,'linprog',lambda *a,**k:SimpleNamespace(
        status=status,success=success,x=np.zeros(13),message='bounded failure'))
    with pytest.raises(ValueError,match='equilibrium optimization'):
        module.static_support(**inputs(nav_robot_model))


def test_solver_success_with_bad_equality_residual_is_rejected(nav_robot_model,monkeypatch):
    module=api()
    monkeypatch.setattr(module,'linprog',lambda *a,**k:SimpleNamespace(
        status=0,success=True,x=np.zeros(13),message='bad result'))
    with pytest.raises(ValueError,match='equilibrium residual'):
        module.static_support(**inputs(nav_robot_model))


@pytest.mark.parametrize('active', [(),('fr_foot',),('fr_foot','fr_foot','rl_foot'),('unknown','fr_foot','rl_foot')])
def test_missing_or_duplicate_support_cannot_produce_force_targets(nav_robot_model,active):
    with pytest.raises(ValueError):api().static_support(**{**inputs(nav_robot_model),'active_feet':active})


def test_local_contact_jacobian_matches_independent_fk_derivatives(nav_robot_model):
    from integrated_robot_navigation.leg_kinematics import fk_leg
    rng=np.random.default_rng(26)
    for foot in nav_robot_model.feet:
        for _ in range(4):
            q=rng.uniform([-.15,-.65,.85],[.15,-.35,1.2])
            point=np.asarray(fk_leg(nav_robot_model,foot,q))
            actual=api().leg_jacobian_local(nav_robot_model,foot,q,point)
            expected=np.column_stack([(np.asarray(fk_leg(nav_robot_model,foot,q+np.eye(3)[k]*1e-6))
                -np.asarray(fk_leg(nav_robot_model,foot,q-np.eye(3)[k]*1e-6)))/2e-6 for k in range(3)])
            assert np.allclose(actual,expected,atol=1e-9)


def test_leg_gravity_matches_independent_potential_energy_derivative(nav_robot_model):
    args=inputs(nav_robot_model);pose=args['body_pose'].copy()
    angle=.17;c,s=np.cos(angle),np.sin(angle);pose[:3,:3]=np.array([[c,0.,s],[0.,1.,0.],[-s,0.,c]])
    q=args['joints'];_,actual=api().leg_terms(nav_robot_model,q,pose,args['points'])
    base_inverse=np.linalg.inv(nav_robot_model.chains['base_link'].forward(q))
    for foot in nav_robot_model.feet:
        def potential(positions):
            return sum(m*9.81*(pose@base_inverse@nav_robot_model.chains[link].forward(positions)
                @np.r_[local,1.])[2] for link,(m,local) in nav_robot_model.masses.items()
                if link.startswith(foot[:2]+'_'))
        for i,part in enumerate(('hip','thigh','calf')):
            name=foot[:2]+'_'+part+'_joint';plus=dict(q);minus=dict(q)
            plus[name]+=1e-6;minus[name]-=1e-6
            assert actual[foot][i]==pytest.approx((potential(plus)-potential(minus))/2e-6,abs=1e-7)
