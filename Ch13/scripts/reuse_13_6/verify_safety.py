"""Actual abort, latched ownership fault, measured hold and owned cleanup."""
import json
import sys
from pathlib import Path


def verify(path):
    path=Path(path);run=path/'run';summary=json.loads((run/'navigation_summary.json').read_text())
    probe=json.loads((run/'safety_probe.json').read_text());engine=json.loads((run/'engine.json').read_text())
    assert summary['result']==probe['result']=='PASS'
    assert engine['normal_shutdown_requested'] and engine['rx_joined'] and engine['camera_worker_joined'] and engine['upstream_threads_joined']
    assert not engine['final_fault'] and engine['max_force_cap_ratio']<=1.+1e-8
    assert not summary['gateway_last'].get('fault') and not summary['navigation_last'].get('fault')
    assert summary['clean_launch_exits']==11 and summary['launch_exit_code']==0 and not summary['remaining_launch_pids']
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    manipulation=engine['manipulation'];assert manipulation['last_status']['fault']==probe['expected_fault']
    terminals=[e for e in manipulation['arm_events'] if e['event']=='measured_terminal' and e['kind']=='arm']
    assert len(terminals)==1 and terminals[0]['terminal']=='aborted'
    rows=manipulation['arm_observations'];assert any(r['stopping'] for r in rows)
    assert max(abs(v) for v in rows[-1]['qd'])<=.05 and max(r['error'] for r in rows)<=.10
    assert probe['no_auto_resume'] and probe['duplicate_executions']==0
    return dict(result='PASS',case=probe['case'],fault=probe['expected_fault'],actual_terminal='aborted',clean_children=11)


if __name__=='__main__':print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
