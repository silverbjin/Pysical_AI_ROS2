"""Quasi-static spring/contact math; NOT physical G2 acceptance."""
from dataclasses import replace
import importlib.util
import xml.etree.ElementTree as ET
import numpy as np
import pytest


def helper(model):
    assert importlib.util.find_spec('integrated_robot_navigation.contact_transfer'), \
        'geometric CoM alone does not regulate the redundant four-contact load'
    from integrated_robot_navigation.contact_transfer import StanceLoadTransfer
    tree=ET.fromstring(model.urdf)
    for name in model.joint_names:
        joint=tree.find(f"ros2_control/joint[@name='{name}']")
        gain={'hip':200.,'thigh':500.,'calf':750.}[name.split('_')[1]]
        ET.SubElement(joint,'param',name='ch13_kp').text=str(gain)
    from integrated_robot_navigation.model import compile_model
    return StanceLoadTransfer(compile_model(ET.tostring(tree,encoding='unicode')))


def inputs(model):
    from integrated_robot_navigation.model import initial_leg_targets
    return dict(foot='rr_foot',joints=initial_leg_targets(model),rotation=np.eye(3),
        points={f:np.array(p) for f,p in zip(model.feet,[(.25,-.18,0.),(.27,.18,0.),(-.25,-.18,0.),(-.25,.18,0.)])},
        forces=np.array([69.,15.,4.8,60.]),dt=.02,speed=.002,min_force=2.)


def test_three_stance_references_address_the_unreleased_fourth_contact(nav_robot_model):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model)
    result=transfer.correction(**args)
    assert set(result)==set(nav_robot_model.feet)-{'rr_foot'}
    assert result['fr_foot']<0 and result['rl_foot']<0 and result['fl_foot']>0
    assert max(abs(v) for v in result.values())<=.002*.02+1e-12
    # Independent flat spring/base equilibrium. Body translation/roll/pitch
    # remain free; force cannot be predicted with four independent springs.
    h=np.array([[1.,p[1],-p[0]] for p in args['points'].values()])
    stiffness=np.diag([1/transfer.vertical_compliance(f,args['joints'],args['rotation']) for f in nav_robot_model.feet])
    projection=stiffness-stiffness@h@np.linalg.solve(h.T@stiffness@h,h.T@stiffness)
    delta=np.array([result.get(f,0.) for f in nav_robot_model.feet])
    force_change=-projection@delta
    assert force_change[2]<0
    # The requested one-second force-error step must survive free-body
    # translation/roll/pitch coupling even though the fourth reference is held.
    assert force_change[2]==pytest.approx(-args['forces'][2]*args['dt'],abs=1e-10), \
        'independent stance springs attenuated the requested load-release step'
    assert np.linalg.norm(h.T@force_change)<1e-10
    assert np.min(args['forces']+force_change)>0


def test_small_feedback_steps_converge_without_moving_the_selected_reference(nav_robot_model):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model)
    h=np.array([[1.,p[1],-p[0]] for p in args['points'].values()])
    stiffness=np.diag([1/transfer.vertical_compliance(f,args['joints'],args['rotation']) for f in nav_robot_model.feet])
    projection=stiffness-stiffness@h@np.linalg.solve(h.T@stiffness@h,h.T@stiffness)
    original=args['forces'].copy();total=np.zeros(4)
    for _ in range(100):
        correction=transfer.correction(**args)
        delta=np.array([correction.get(f,0.) for f in nav_robot_model.feet])
        assert delta[2]==0 and max(abs(delta))<=.000040000001
        total+=delta;args['forces']=original-projection@total
    assert args['forces'][2]<2. and np.min(args['forces'][[0,1,3]])>2.
    assert max(abs(total))<.002


def test_missing_native_stiffness_cannot_enable_this_model(nav_robot_model):
    helper(nav_robot_model)
    from integrated_robot_navigation.contact_transfer import StanceLoadTransfer
    with pytest.raises(ValueError,match='stiffness'):StanceLoadTransfer(nav_robot_model)


@pytest.mark.parametrize('change',[dict(dt=-.01),dict(dt=.21),dict(forces=[1.,2.,float('nan'),4.]),dict(rotation=np.zeros((3,3)))])
def test_invalid_input_does_not_produce_a_reference(nav_robot_model,change):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model);args.update(change)
    with pytest.raises(ValueError):transfer.correction(**args)


def test_zero_credit_produces_no_correction_but_unconfirmed_low_force_stays_controlled(nav_robot_model):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model)
    assert not any(transfer.correction(**{**args,'dt':0.}).values())
    args['forces'][2]=1.99
    assert any(transfer.correction(**args).values()), 'first low sample incorrectly ended load regulation'
    args['forces'][2]=0.
    assert not any(transfer.correction(**args).values())


@pytest.mark.parametrize('selected',range(4))
def test_coupled_equilibrium_step_is_correct_for_every_swing_selection(nav_robot_model,selected):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model)
    args['foot']=nav_robot_model.feet[selected]
    args['forces']=np.full(4,60.);args['forces'][selected]=4.8
    args['forces'][3-selected]=15.
    delta_map=transfer.correction(**args)
    h=np.array([[1.,p[1],-p[0]] for p in args['points'].values()])
    stiffness=np.diag([1/transfer.vertical_compliance(f,args['joints'],args['rotation']) for f in nav_robot_model.feet])
    projection=stiffness-stiffness@h@np.linalg.solve(h.T@stiffness@h,h.T@stiffness)
    delta=np.array([delta_map.get(f,0.) for f in nav_robot_model.feet])
    response=-projection@delta
    assert response[selected]==pytest.approx(-4.8*.02,abs=1e-10)
    assert np.linalg.norm(h.T@response)<1e-10
    assert delta[selected]==0


def test_inverse_coupling_never_overrides_the_original_reference_rate_cap(nav_robot_model):
    transfer=helper(nav_robot_model);args=inputs(nav_robot_model)
    args.update(forces=[2000.,2000.,1000.,2000.],dt=.2)
    result=transfer.correction(**args)
    assert max(abs(v) for v in result.values())==pytest.approx(.002*.2,abs=1e-12)
    assert transfer.last_linear_model['command_rate_scale']<1.
