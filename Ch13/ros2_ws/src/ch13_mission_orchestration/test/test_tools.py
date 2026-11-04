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


def test_lift_cancel_waits_for_actual_execution_not_planning_phase():
    from ch13_mission_orchestration.tools import lift_interrupt
    assert lift_interrupt({'task_phase':'LIFT','manipulation_phase':'READY','clock_ns':100},None)==(None,False)
    progress={'task_phase':'LIFT','manipulation_phase':'EXECUTING','clock_ns':2_000_000_000}
    assert lift_interrupt(progress,None)==(2_000_000_000,False)
    progress['clock_ns']=3_000_000_000
    assert lift_interrupt(progress,2_000_000_000)==(2_000_000_000,True)


def test_verifier_preserves_an_existing_verdict(tmp_path):
    import json,subprocess,sys
    root=Path(__file__).resolve().parents[5];run=tmp_path/'run';run.mkdir()
    original='{"result":"PASS","preserve":"original verdict"}\n'
    (tmp_path/'mission_verification.json').write_text(original)
    (run/'bt_summary.json').write_text(json.dumps({'profile':'actual','case':'cancel'}))
    (run/'navigation_summary.json').write_text('{}')
    for name in ('pre_residual','post_residual'):(tmp_path/(name+'.json')).write_text('{"result":"PASS"}')
    result=subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_7/verify_mission.py'),str(tmp_path)],capture_output=True,text=True)
    assert result.returncode!=0
    assert (tmp_path/'mission_verification.json').read_text()==original
