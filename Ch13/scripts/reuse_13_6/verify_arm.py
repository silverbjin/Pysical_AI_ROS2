"""Measured motion and true action terminal, independent of client tolerance."""
import json
import sys
from pathlib import Path
import numpy as np


def verify(path):
    path=Path(path);summary=json.loads((path/'run/navigation_summary.json').read_text())
    probe=json.loads((path/'run/arm_probe.json').read_text());engine=summary['engine'];manipulation=engine['manipulation']
    assert summary['result']=='PASS' and engine['normal_shutdown_requested']
    assert engine['rx_joined'] and engine['upstream_threads_joined'] and engine['camera_worker_joined']
    assert summary['launch_exit_code']==0 and not summary['remaining_launch_pids']
    assert summary['clean_launch_exits']==len(summary['owned_launch_pids'])==11
    assert json.loads((path/'post_residual.json').read_text())['result']=='PASS'
    rows=manipulation['arm_observations'];excursion=np.ptp([r['q'] for r in rows],axis=0)
    case=probe['case'];expected={'normal':'succeeded','cancel':'canceled','loss':'aborted'}[case]
    terminals=[r for r in manipulation['arm_events'] if r['event']=='measured_terminal' and r['kind']=='arm']
    assert len(terminals)==1 and terminals[0]['terminal']==expected
    assert max(r['error'] for r in rows)<=.10
    assert engine['max_force_cap_ratio']<=1.+1e-8 and not engine['final_fault']
    if case=='normal':
        assert np.all(excursion>=.005),('no actual six-axis motion',excursion.tolist())
        assert manipulation['last_status']['phase']=='REVOKED' and not manipulation['last_status']['fault']
        grips=[r for r in probe['records'] if r['kind']=='gripper'];assert len(grips)==2
        for r in grips:
            assert abs(r['joint7']-r['target'])<=.002 and abs(r['joint7']+r['joint8'])<=.002
    else:
        assert any(r['stopping'] for r in rows)
        assert max(abs(x) for x in rows[-1]['qd'])<=.05
        if case=='loss':assert manipulation['last_status']['fault']=='MISSION_EXPIRED'
        else:assert not manipulation['last_status']['fault']
    return dict(result='PASS',case=case,actual_excursion_rad=excursion.tolist(),
                peak_tracking_error_rad=max(r['error'] for r in rows),terminal=expected,
                clean_children=summary['clean_launch_exits'],control_profile=manipulation.get('control_profile','v1'))


if __name__=='__main__':print(json.dumps([verify(p) for p in sys.argv[1:]],indent=2))
