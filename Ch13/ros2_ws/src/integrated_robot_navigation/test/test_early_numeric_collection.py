"""Transport collection precedes model work; application still needs all checks."""
from copy import deepcopy
import numpy as np
import pytest
from test_async_xyz_owner import ready_xyz,complete_xyz
from test_async_load_owner import next_capture


def pending(model):
    m,b,q,p,points,f=ready_xyz(model)
    m._transfer_stance_load(b,q,p,points,f,.02);complete_xyz(m,f)
    b=next_capture(m,b)
    return m,b,q,p,points,f


def test_ready_reply_is_collected_before_slow_measure_but_sensor_failure_prevents_commit(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=pending(nav_robot_model);peer=m._load_transfer;before=deepcopy(m._targets)
    def measure(*a,**kw):
        assert peer.reply is None,'ready numerical reply still waits behind model safety work'
        assert m._load_collected_reply is not None
        assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)
        raise ValueError('controlled current sensor failure')
    monkeypatch.setattr(m,'_measure',measure)
    result=m.advance(b,(.005,0.,0.),m._last_ros,m._last_wall)
    assert result.state=='FAULT'
    assert m._load_collected_reply is None
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


@pytest.mark.parametrize('invalidate',['stop','generation','age'])
def test_early_collection_does_not_authorize_unowned_stale_or_stopped_results(nav_robot_model,monkeypatch,invalidate):
    m,b,q,p,points,f=pending(nav_robot_model);before=deepcopy(m._targets)
    assert hasattr(m,'_collect_load_transfer'),'no bounded pre-model result collection'
    m._collect_load_transfer(m._last_wall)
    assert m._load_collected_reply is not None
    if invalidate=='stop':
        m.request_stop(urgent=True)
        assert m._load_collected_reply is None
        return
    if invalidate=='generation':m.generation+=1
    # An actually collected message can age during model work. Keep the same
    # original 200ms receipt limit at the later application boundary.
    receipt=min(v[1] for v in m._load_collected_reply['context']['samples'].values())
    monkeypatch.setattr('integrated_robot_navigation.gait.time.monotonic_ns',lambda:receipt+(200_000_001 if invalidate=='age' else 30_000_000))
    with pytest.raises(ValueError,match='ownership|stale original'):
        m._transfer_stance_load(b,q,p,points,f,.02)
    assert m._load_collected_reply is None
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)


def test_collected_result_can_be_committed_only_once_after_current_validation(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=pending(nav_robot_model);before=deepcopy(m._targets)
    assert hasattr(m,'_collect_load_transfer'),'no bounded pre-model result collection'
    m._collect_load_transfer(m._last_wall)
    monkeypatch.setattr('integrated_robot_navigation.gait.time.monotonic_ns',lambda:m._last_wall)
    m._transfer_stance_load(b,q,p,points,f,.02)
    after=deepcopy(m._targets)
    assert any(not np.array_equal(before[n],after[n]) for n in m.model.feet)
    m._transfer_stance_load(b,q,p,points,f,.02)
    assert all(np.array_equal(after[n],m._targets[n]) for n in m.model.feet)


def test_failed_early_collection_reports_failed_job_not_previous_success(nav_robot_model,monkeypatch):
    m,b,q,p,points,f=pending(nav_robot_model);peer=m._load_transfer;before=deepcopy(m._targets)
    m.load_transfer_observation=dict(numeric_input={'job':60},original_snapshot={'capture':60})
    peer.last_input={'job':61,'reference':[1.,2.,3.]};peer.last_context={'capture':61}
    peer.last_input_id=61;peer.last_attempt={'solver_status':4}
    def fail(**kw):raise ValueError('native XYZ solver status 4')
    monkeypatch.setattr(peer,'poll',fail)
    with pytest.raises(ValueError,match='solver status 4'):m._collect_load_transfer(m._last_wall)
    report=m.load_transfer_observation
    assert report['numeric_input']==peer.last_input
    assert report['original_snapshot']==peer.last_context
    assert report['numeric_input_job_id']==61
    assert report['attempt']==peer.last_attempt
    peer.last_input['reference'][0]=99.;peer.last_context['capture']=62
    assert report['numeric_input']['reference']==[1.,2.,3.] and report['original_snapshot']=={'capture':61}
    assert all(np.array_equal(before[n],m._targets[n]) for n in m.model.feet)
