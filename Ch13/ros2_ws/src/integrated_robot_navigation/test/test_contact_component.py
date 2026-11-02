"""FK/observation sequencing only; this fixture is not native dynamics."""
from dataclasses import asdict,replace
import importlib.util
import numpy as np
import pytest
from guard_fixture import bundle
from integrated_robot_navigation.leg_kinematics import fk_leg,ik_leg


def frame(model,stamp=1_000_000_000,receipt=10_000_000_000,foot=None,lift=0.,force=30.):
    value=bundle(model,stamp,receipt);q=dict(value.joints.data['position'])
    if foot:
        names=[foot[:2]+'_'+p+'_joint' for p in ('hip','thigh','calf')]
        old=tuple(q[n] for n in names);target=np.array(fk_leg(model,foot,old));target[2]+=lift
        q.update(zip(names,ik_leg(model,foot,target,old)))
    forces=[force if f==foot else 30. for f in model.feet]
    value=replace(value,joints=replace(value.joints,data={**value.joints.data,'position':q}),
        contacts=replace(value.contacts,data={**value.contacts.data,'forces':tuple(forces),
            'touching':tuple(v>=2. for v in forces),'forces_world':tuple((0.,0.,v) for v in forces),
            'force_vectors_valid':True}))
    return dict(samples=asdict(value),ros_ns=stamp,wall_ns=receipt)


def tracker(model):
    assert importlib.util.find_spec('integrated_robot_navigation.contact_component'), 'bounded contact-component observer missing'
    from integrated_robot_navigation.contact_component import ContactTransitionTracker
    return ContactTransitionTracker(model,frame(model))


def test_four_observed_unload_lift_return_sequences_are_required(nav_robot_model):
    value=tracker(nav_robot_model);r=1_000_000_000;w=10_000_000_000
    for foot in nav_robot_model.feet:
        r+=20_000_000;w+=20_000_000;value.update(frame(nav_robot_model,r,w,foot,.002,0.))
        r+=100_000_000;w+=100_000_000;value.update(frame(nav_robot_model,r,w,foot,.006,0.))
        r+=20_000_000;w+=20_000_000;value.update(frame(nav_robot_model,r,w,foot,0.,30.))
    report=value.report()
    assert report['all_four_contacts_completed'] is True
    assert set(report['completed_feet'])==set(nav_robot_model.feet)
    assert all(v>=.005 for v in report['maximum_lift_m'].values())
    assert report['scope']=='observed_contact_component_not_full_G2_acceptance'


def test_contact_loss_without_actual_fk_lift_cannot_complete(nav_robot_model):
    value=tracker(nav_robot_model);foot=nav_robot_model.feet[0]
    value.update(frame(nav_robot_model,1_020_000_000,10_020_000_000,foot,0.,0.))
    value.update(frame(nav_robot_model,1_140_000_000,10_140_000_000,foot,0.,0.))
    value.update(frame(nav_robot_model,1_160_000_000,10_160_000_000,foot,0.,30.))
    assert not value.report()['completed_feet']


def test_duplicate_capture_does_not_satisfy_original_100ms_dwell(nav_robot_model):
    value=tracker(nav_robot_model);foot=nav_robot_model.feet[0]
    first=frame(nav_robot_model,1_020_000_000,10_020_000_000,foot,.006,0.)
    value.update(first);value.update(first)
    value.update(frame(nav_robot_model,1_040_000_000,10_180_000_000,foot,0.,30.))
    assert not value.report()['completed_feet']


def test_stale_or_unattested_forces_cannot_be_component_evidence(nav_robot_model):
    value=tracker(nav_robot_model);item=frame(nav_robot_model)
    item['ros_ns']+=200_000_001
    with pytest.raises(ValueError):value.update(item)
    item=frame(nav_robot_model);item['samples']['contacts']['data']['force_vectors_valid']=False
    with pytest.raises(ValueError):value.update(item)


def test_component_completion_keeps_original_incomplete_G2_result_unchanged():
    from integrated_robot_navigation import contact_component as module
    assert hasattr(module,'component_outcome'), 'explicit non-admission component outcome missing'
    checks=dict(forward=False,left=False,right=False,dart_contact_contract=False,
        normal_runtime_exit=True,normal_engine_exit=True,carry_terminal_received=True,
        joint_tf_ownership=True,contact_support=True,sensor_freshness=True,stability=True,native_ctrl_observed=True)
    result=dict(gate='G2',status='FAIL',required_checks=list(checks),checks=checks)
    report=module.component_outcome(result,dict(all_four_contacts_completed=True),
        protocol_finished=True,dart_observed=True)
    assert report['observations_complete'] and not report['full_G2_acceptance']
    assert result['status']=='FAIL' and result['checks']['forward'] is False
    checks['normal_runtime_exit']=False
    assert not module.component_outcome(result,dict(all_four_contacts_completed=True),
        protocol_finished=True,dart_observed=True)['observations_complete']
