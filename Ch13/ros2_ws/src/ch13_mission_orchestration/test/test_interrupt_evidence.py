import json
from ch13_mission_orchestration.tasks import TaskPort
from ch13_mission_orchestration.session import Session


def test_bt_pick_interrupt_records_actual_hold_and_post_settle(tmp_path):
    port=TaskPort();port.cancel('user_cancel');session=Session(port)
    session.session=session.observed_session='s';clock=[0];phases=[]
    session.goals.terminals=[5]
    def snapshot():
        clock[0]+=1_000_000_000
        return {'clock_ns':clock[0],'platform':{'stationary_ready':True}}
    def until(predicate,timeout):
        for _ in range(10):
            if predicate():return True
        return False
    def callback(**kwargs):
        (tmp_path/'pick_mission.json').write_text(json.dumps({'stages':[{'phase':'LIFT'}],'planning':[]}))
        raise AssertionError('canceled native action terminal')
    session.pick_work(callback,evidence=tmp_path,node=None,until=until,snapshot=snapshot,
        status=lambda:{'phase':'EXECUTING'},control={'set_phase':phases.append})
    saved=json.loads((tmp_path/'pick_mission.json').read_text())
    assert phases==['HOLD','POST_SETTLE']
    assert [r['phase'] for r in saved['stages'] if 'phase' in r]==['LIFT','HOLD','POST_SETTLE']
    assert any(r.get('held_cancel') for r in saved['stages'])
