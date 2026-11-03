from pathlib import Path
import pytest
from ch13_mission_orchestration.tools import validate_build,verify_bt


@pytest.mark.parametrize('path',['/home/jinho/ch13_reuse_13_6_build/sub','/home/jinho','/home/jinho/ch13_reuse_r5_build'])
def test_build_rejects_overlap_with_existing_installs(path):
    with pytest.raises(ValueError):validate_build(path)


def test_build_allows_separate_13_7_path():
    assert validate_build('/home/jinho/ch13_reuse_13_7_build').name=='ch13_reuse_13_7_build'


def test_verifier_rejects_mock_as_actual_even_with_success():
    result=verify_bt(dict(profile='mock',terminal='SUCCESS',port={},worker_joined=True))
    assert result['result']=='FAIL'


def test_verifier_rejects_pick_after_cancel_and_unjoined_worker():
    data=dict(profile='actual',terminal='ABORTED',case='cancel',session='s',worker_joined=False,
        worker={'exit_code':0},port={'error':'','closed':True,'requested':['navigate','pick'],
        'events':[{'event':'injection'}],'completed':{}})
    assert verify_bt(data)['result']=='FAIL'
