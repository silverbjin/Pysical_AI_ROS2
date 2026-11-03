"""Check same-session live authority and owned cleanup from saved raw status."""
import json
import sys
from pathlib import Path


def verify(path):
    path=Path(path)
    summary=json.loads((path/'run/navigation_summary.json').read_text())
    assert summary['result']=='PASS',summary.get('error')
    result=summary['manipulation_handoff']
    assert result['result']=='PASS'
    engine=summary['engine']
    assert engine['result']=='COMPLETED' and engine['normal_shutdown_requested']
    assert engine['rx_joined'] and engine['upstream_threads_joined'] and engine['camera_worker_joined']
    assert engine['max_force_cap_ratio']<=1.+1e-8 and not engine['final_fault']
    assert summary['launch_exit_code']==0 and not summary['remaining_launch_pids']
    assert summary['clean_launch_exits']==len(summary['owned_launch_pids'])==11
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    rows=[json.loads(line) for line in (path/'run/manipulation_status.jsonl').read_text().splitlines()]
    assert rows and all(r['session']==result['session'] for r in rows)
    assert engine['manipulation']['last_status']['session']==result['session']
    assert all(b['stamp_ns']>=a['stamp_ns'] and b['decision_wall']>=a['decision_wall'] for a,b in zip(rows,rows[1:]))
    final=engine['manipulation']['last_status']
    case=result['case']
    ready=[r for r in rows if r['phase']=='READY']
    duration=None
    if case=='hold':
        assert ready and final['phase']=='REVOKED' and not final['fault']
        duration=ready[-1]['decision_wall']-ready[0]['decision_wall']
        assert duration>=1.9 and ready[-1]['stamp_ns']>ready[0]['stamp_ns']
        assert len({r['capture_ns'] for r in ready})>=2
    else:
        expected={'expire':'MISSION_EXPIRED','old_session':'SESSION_MISMATCH','duplicate':'DUPLICATE_OWNER:mission'}[case]
        assert final['phase']=='FAULT' and final['fault']==expected,final
        if case=='old_session':assert not ready
    return dict(result='PASS',case=case,session=result['session'],engine_pid=engine['pid'],
                ready_wall_s=duration,final_phase=final['phase'],fault=final['fault'],
                clean_children=summary['clean_launch_exits'])


if __name__=='__main__':
    results=[verify(p) for p in sys.argv[1:]]
    print(json.dumps(results,indent=2))
