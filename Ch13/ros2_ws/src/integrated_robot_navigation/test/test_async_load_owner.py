"""Only the model owner may commit a fresh, reference-bound numeric result."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from test_coupled_contact_integration import fixture


class NumericPeer:
    asynchronous=True
    def __init__(self,kernel):
        self.gains=kernel.gains;self.pending=None;self.reply=None;self.requests=[]
        self.last_model={'scope':'unit_numeric_peer_not_native_physics'};self.last_attempt={}
        self.discards=0
    def submit(self,args,context):
        assert self.pending is None
        self.pending=deepcopy(context);self.requests.append(deepcopy(args))
    def poll(self,**_):
        if self.reply is None:return None
        result=self.reply;self.reply=None;self.pending=None;return result
    def snapshot(self):return {'pending':self.pending is not None}
    def discard(self):self.discards+=1;self.pending=None;self.reply=None


def ready(model):
    m,bundle,q,pose,points,foot=fixture(model)
    m._load_transfer=NumericPeer(m._load_transfer)
    return m,bundle,q,pose,points,foot


def next_capture(m,bundle,elapsed=20_000_000):
    m._last_ros+=elapsed;m._last_wall+=elapsed
    return replace(bundle,**{key:replace(getattr(bundle,key),
        stamp_ns=getattr(bundle,key).stamp_ns+elapsed,
        received_ns=getattr(bundle,key).received_ns+elapsed,
        sequence=getattr(bundle,key).sequence+elapsed)
        for key in ('joints','imu','body','contacts')})


def complete(m,foot,delta=1e-5):
    peer=m._load_transfer
    peer.reply=dict(delta={f:delta if f==foot else 0. for f in m.model.feet},
        context=deepcopy(peer.pending),submitted_wall_ns=m._last_wall,
        received_wall_ns=m._last_wall+20_000_000,computed_wall_ns=m._last_wall+2_000_000)


def test_submit_does_not_advance_height_or_duplicate_the_unload_ramp(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model);before=deepcopy(m._targets)
    assert m._transfer_stance_load(b,q,p,points,f,.02) is True
    assert len(m._load_transfer.requests)==1
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)
    assert m.load_transfer_observation['outcome']=='submitted'


def test_result_commits_once_and_pipelines_from_the_updated_owned_reference(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model)
    m._transfer_stance_load(b,q,p,points,f,.02);before=float(m._targets[f][2])
    complete(m,f);b=next_capture(m,b)
    assert m._transfer_stance_load(b,q,p,points,f,.02) is True
    assert m._targets[f][2]==pytest.approx(before+1e-5)
    assert len(m._load_transfer.requests)==2
    assert m._load_transfer.requests[1]['reference_z'][f]==pytest.approx(before+1e-5)
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert m._targets[f][2]==pytest.approx(before+1e-5)
    assert len(m._load_transfer.requests)==2


def test_numeric_dt_cannot_exceed_actual_elapsed_reference_time(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model);m._transfer_stance_load(b,q,p,points,f,.02)
    complete(m,f,delta=2e-5);b=next_capture(m,b,5_000_000);before=deepcopy(m._targets)
    with pytest.raises(ValueError,match='elapsed reference rate'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_next_queue_failure_cannot_commit_an_unissued_reference(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=ready(nav_robot_model);m._transfer_stance_load(b,q,p,points,f,.02)
    complete(m,f);b=next_capture(m,b);before=deepcopy(m._targets)
    def reject(*_):raise ValueError('transition optimization queue rejected')
    monkeypatch.setattr(m._load_transfer,'submit',reject)
    with pytest.raises(ValueError,match='queue rejected'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_original_receipt_age_is_checked_at_actual_result_receipt(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model)
    b=replace(b,**{key:replace(getattr(b,key),stamp_ns=getattr(b,key).stamp_ns-180_000_000,
        received_ns=getattr(b,key).received_ns-180_000_000,
        sequence=getattr(b,key).sequence-180_000_000) for key in ('joints','imu','body','contacts')})
    m._transfer_stance_load(b,q,p,points,f,.02);complete(m,f)
    m._load_transfer.reply['received_wall_ns']=m._last_wall+27_000_000
    b=next_capture(m,b,10_000_000);before=deepcopy(m._targets)
    with pytest.raises(ValueError,match='stale original snapshot'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


@pytest.mark.parametrize('change',['generation','reference','ros_age','wall_age'])
def test_old_or_unowned_result_cannot_change_a_reference(nav_robot_model,change):
    m,b,q,p,points,f=ready(nav_robot_model);m._transfer_stance_load(b,q,p,points,f,.02)
    complete(m,f);b=next_capture(m,b);before=deepcopy(m._targets)
    if change=='generation':m.generation+=1
    elif change=='reference':m.reference_body[0,3]+=.001
    elif change=='ros_age':m._last_ros+=200_000_001
    else:m._last_wall+=200_000_001
    with pytest.raises(ValueError,match='transition optimization'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_current_servo_error_is_checked_after_the_old_numeric_snapshot(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model);m._transfer_stance_load(b,q,p,points,f,.02)
    complete(m,f);b=next_capture(m,b);before=deepcopy(m._targets)
    q=dict(q);q['rr_calf_joint']+=.2
    with pytest.raises(ValueError,match='current servo effort'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


@pytest.mark.parametrize('stop',['explicit_stop','fault'])
def test_stop_or_fault_invalidates_outstanding_math_without_releasing_legs(nav_robot_model,stop):
    m,b,q,p,points,f=ready(nav_robot_model);m._transfer_stance_load(b,q,p,points,f,.02)
    before=deepcopy(m._targets)
    if stop=='explicit_stop':m.request_stop(urgent=True)
    else:m._fail('transition optimization worker failed')
    assert m._load_transfer.discards==1
    assert len(m._load_transfer.requests)==1
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_zero_velocity_pause_invalidates_the_inflight_numeric_reference(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model)
    m._transfer_stance_load(b,q,p,points,f,.02)
    result=m.advance(b,(0.,0.,0.),m._last_ros,m._last_wall)
    assert result.state!='FAULT',result.reason
    assert m._paused and m._load_transfer.discards==1


def test_cancelled_capture_cannot_be_submitted_again_without_new_feedback(nav_robot_model):
    m,b,q,p,points,f=ready(nav_robot_model)
    m._transfer_stance_load(b,q,p,points,f,.02);m._discard_load_transfer()
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert len(m._load_transfer.requests)==1
    assert m.load_transfer_observation['outcome']=='awaiting_new_capture'
    b=next_capture(m,b)
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert len(m._load_transfer.requests)==2
