"""Transient load correction must not become the next step's neutral pose."""
import numpy as np
import pytest
from test_stance_load_owner import configured


def test_unload_compensation_cannot_redefine_neutral_landing_reference(nav_robot_model):
    m,p,a=configured(nav_robot_model);neutral=dict(m._stance_reference_z)
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    assert m._stance_reference_z==neutral, 'temporary three-stance compensation leaked into permanent preload'


def test_after_contact_restoration_is_bounded_and_exact(nav_robot_model):
    m,p,a=configured(nav_robot_model);neutral={f:v.copy() for f,v in m._targets.items()}
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    assert hasattr(m,'_restore_stance_load'), 'no bounded post-contact owner releases temporary offsets'
    m.phase='SETTLE';last={f:v.copy() for f,v in m._targets.items()}
    for _ in range(300):
        done=m._restore_stance_load(.02)
        assert max(abs(m._targets[f][2]-last[f][2]) for f in m.model.feet)<=.00004000001
        assert all(np.array_equal(m._targets[f][:2],neutral[f][:2]) for f in m.model.feet)
        last={f:v.copy() for f,v in m._targets.items()}
        if done:break
    assert done
    assert all(np.array_equal(m._targets[f],neutral[f]) for f in m.model.feet)


@pytest.mark.parametrize('change',[dict(stopping=True),dict(state='FAULT'),dict(phase='SWING')])
def test_restore_never_commands_during_stop_fault_or_before_landing(nav_robot_model,change):
    m,p,a=configured(nav_robot_model)
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    m.phase='SETTLE'
    for k,v in change.items():setattr(m,k,v)
    before={f:v.copy() for f,v in m._targets.items()}
    assert hasattr(m,'_restore_stance_load'), 'post-contact restoration owner missing'
    assert not m._restore_stance_load(.02)
    assert all(np.array_equal(m._targets[f],before[f]) for f in m.model.feet)


@pytest.mark.parametrize('resume',[False,True])
def test_full_advance_cannot_begin_next_shift_before_neutral_references_return(nav_robot_model,resume):
    m,p,a=configured(nav_robot_model);neutral={f:v.copy() for f,v in m._targets.items()}
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    m.phase='SETTLE';m._phase_start=p.ros
    if resume:m.state='STAND'
    previous=None
    for _ in range(300):
        p.tick(m,previous)
        previous=m.advance(p.state,(.0001,0.,0.),p.ros,p.wall)
        assert previous.state!='FAULT',previous.reason
        if m.phase=='SHIFT':
            assert not m._load_transfer_rest_z
            assert all(np.array_equal(m._targets[f],neutral[f]) for f in m.model.feet)
            assert m._index==(0 if resume else 1)
            return
    pytest.fail('restoration never released the next planned shift')


def test_pending_application_cannot_extend_the_restore_deadline(nav_robot_model):
    m,p,a=configured(nav_robot_model)
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    m.phase='SETTLE';m._phase_start=p.ros-5_300_000_000
    p.tick(follow=False)
    result=m.advance(p.state,(.0001,0.,0.),p.ros,p.wall,reference_permitted=False)
    assert result.state=='FAULT' and result.reason=='stance preload restore timeout'
    assert result.joint_targets is None and not m.fault_stop_confirmed
