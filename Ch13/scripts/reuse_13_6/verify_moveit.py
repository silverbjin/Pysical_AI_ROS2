"""Independent M3 evidence checks; no planner success substitutes actual state."""
import json
import sys
from pathlib import Path


def verify(path):
    path=Path(path);run=path/'run';summary=json.loads((run/'navigation_summary.json').read_text())
    assert summary['result']=='PASS',summary.get('error')
    assert not summary['gateway_last'].get('fault') and not summary['navigation_last'].get('fault')
    engine=summary['engine'];probe=json.loads((run/'moveit_probe.json').read_text())
    assert engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['upstream_threads_joined'] and engine['camera_worker_joined']
    assert not engine['final_fault'] and engine['max_force_cap_ratio']<=1+1e-8
    assert summary['planner_stopped_before_engine'] and summary['clean_launch_exits']==12
    assert summary['launch_exit_code']==0 and not summary['remaining_launch_pids']
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    records=probe['records'];measurements=probe['measurements']
    assert len(measurements)==3
    assert all(m['position_error_m']<=.01 and m.get('orientation_error_rad',0.)<=.05 for m in measurements)
    plans=[r for r in records if r['kind']=='plan']
    assert [r['error_code']==1 for r in plans]==[True,True,False,False,True]
    cart=[r for r in records if r['kind']=='cartesian'];assert len(cart)==1 and cart[0]['fraction']==1.
    validity=[r for r in records if r['kind']=='state_validity']
    assert [r['valid'] for r in validity]==[True,False,True]
    assert 'planning_collision_fixture' in json.dumps(validity[1]['contacts'])
    executions=[r for r in records if r['kind']=='execute']
    assert [(r['status'],r['error_code']) for r in executions[:3]]==[(4,0)]*3
    assert executions[3]['status']==5
    events=engine['manipulation']['arm_events']
    canceled=[e for e in events if e['event']=='measured_terminal' and e.get('terminal')=='canceled']
    assert len(canceled)==1 and any(e['event']=='cancel_ack' and e['goal']==canceled[0]['goal'] and e['wall']<=canceled[0]['wall'] for e in events)
    assert engine['manipulation']['last_status']['phase']=='REVOKED'
    return dict(result='PASS',measurements=measurements,cartesian_fraction=1.,actual_cancel=True,clean_children=12)


if __name__=='__main__':print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
