import time
import threading
import pytest
from ch13_mission_orchestration.tasks import TaskPort
from ch13_mission_orchestration.session import Session,admit_observation


def sample():
    return dict(capture_ns=1_000_000_000,capture_wall=10.,tf_stamp_ns=950_000_000,
        first_receipt_wall=10.01,source_gids={'rgb':'gid'},rgb_sha256='a'*64,
        point=[.5,0.,.4],source='actual_Renderer_RGBD_known_upright_cylinder_fit',cylinder_fit={})


def test_observation_copy_keeps_original_time_and_rejects_stale():
    s=sample(); output=admit_observation(s,1_100_000_000,10.1)
    assert output['capture_ns']==1_000_000_000 and output['first_receipt_wall']==10.01
    output['point'][0]=99; assert s['point'][0]==.5
    with pytest.raises(ValueError):admit_observation(s,1_400_000_000,10.4)


def test_gate_waits_for_bt_request_and_cancel_is_not_completion():
    port=TaskPort(); session=Session(port)
    def until(predicate,timeout):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return True
            time.sleep(.001)
        return False
    done=[]
    thread=threading.Thread(target=lambda:(session.await_step('navigate',until),done.append(True)))
    thread.start(); time.sleep(.02); assert not done
    port.submit('navigate'); thread.join(1); assert done
    port.cancel('user'); assert session.cancel_requested()
    assert 'navigate' not in port.snapshot()['completed']


def test_find_snapshot_cannot_authorize_different_session():
    port=TaskPort(); session=Session(port); session.session='one'
    session.observed_session='two'
    with pytest.raises(ValueError):session.validate_session()
