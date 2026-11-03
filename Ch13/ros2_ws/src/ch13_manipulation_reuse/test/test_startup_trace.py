import json
import pytest
from ch13_navigation_reuse.startup_trace import StartupTrace,require_startup_service


def test_first_fault_preserves_original_times_pending_and_bounded_history(tmp_path):
    trace=StartupTrace(tmp_path,'gateway',capacity=3)
    info=dict(receipt_wall=10.,publisher_gid=b'owner',relay_gid='relay')
    for i in range(5):trace.packet('clock',i,info,10.01+i*.001,0,None)
    pending={'base':(1100,10.,('base',None,info))}
    trace.fault('future',pending,1100,10.02,10.06)
    trace.packet('clock',2000,info,11.,2000,11.)
    trace.fault('later',{},2000,11.,11.)
    trace.write();data=json.loads((tmp_path/'gateway_startup_trace.json').read_text())
    assert data['fault']['reason']=='future' and data['fault']['clock_receipt_wall']==10.02
    assert data['fault']['pending'][0]['receipt_wall']==10.
    assert data['fault']['pending'][0]['stamp_ns']==1100
    assert len(data['events'])==3 and data['discarded_events']==2
    assert data['events'][-1]['native_receipt_wall']==10.
    assert data['events'][-1]['process_wall']==10.014


@pytest.mark.parametrize('name',['platform/arm','gateway/arm','navigation/enable','navigation/release','unknown'])
def test_startup_only_blocks_all_motion_admission(name):
    with pytest.raises(ValueError):require_startup_service(name)


def test_startup_only_allows_normal_recovery():
    require_startup_service('platform/shutdown');require_startup_service('navigation/idle')
