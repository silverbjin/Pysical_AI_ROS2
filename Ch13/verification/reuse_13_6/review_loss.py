"""Offline review of the v13 injected raw-loss watchdog cascade.

Preserves the original 13.5 FAIL and changes no runtime or stop threshold.
The specific expired platform field was not recorded; no such diagnosis is made.
"""
import hashlib,json,math,sys
from pathlib import Path


def assess(data):
    try:
        s,e,rows,tr,original=(data[k] for k in ('summary','engine','rows','trace','original'))
        checks=original['checks']
        required={'zero_command','unique_samples','probe_pass','normal_engine','threads','force_cap','processes',
                  'all_physics_native_joint_limits','prepared_zero_before_motion','platform_no_unexpected_fault',
                  'actual_motion_before_cancel_or_loss','rx_no_exception'}
        assert required<=checks.keys() and original['gate']=='section_13_5_edu_stop_v2'
        assert original['result']=='FAIL' and [k for k,v in checks.items() if v is not True]==['platform_no_unexpected_fault']
        assert data['residual']['result']=='PASS'
        assert s['case']=='raw_loss' and s['injection']=='owned_publisher_pause_with_identity_preserved'
        assert s['injected_boundary_pid'] in s['owned_launch_pids'] and s['no_auto_resume_after_raw_return'] is True
        gateway=s['gateway_last'];fault=tr['fault'];raw=gateway['source_receipts']['raw']
        assert gateway['mode']=='FAULT' and gateway['fault']==fault['reason']==e['final_fault']=='INPUT_OR_CLOCK_TIMEOUT'
        assert e['final_mode']=='FAULT' and all(v==1 for v in gateway['counts'].values())
        assert {'clock','raw','base','joints','relay'}<=gateway['counts'].keys()
        expiry=fault['decision_wall']-raw['receipt_wall']
        # Status uses tick-entry time; trace records a later call in that tick.
        # Both must meet the existing budget, not have identical timestamps.
        assert .30<=expiry<=.35 and .30<=s['raw_expiry_decision_latency_s']<=.35
        assert 0<=fault['decision_wall']-fault['clock_receipt_wall']<=.30
        assert 0<=fault['clock_ns']-raw['stamp_ns']<=300_000_000
        assert len(rows)>3
        for before,after in zip(rows,rows[1:]):
            assert 0<after['wall']-before['wall']<=.30 and after['sim_s']>before['sim_s']
        assert all(math.isfinite(r[k]) for r in rows for k in ('sim_s','wall','vx','wz'))
        first=next(i for i,r in enumerate(rows) if r['fault'])
        assert first>0 and any(r['mode']=='ARMED' and abs(r['vx'])>0 for r in rows[:first])
        assert all(not r['fault'] for r in rows[:first])
        delay=rows[first]['wall']-raw['receipt_wall']
        assert .30<=delay<=.35  # Existing probe's expiry decision budget.
        assert all(r['mode']=='FAULT' and r['fault']=='INPUT_OR_CLOCK_TIMEOUT' and r['vx']==r['wz']==0 for r in rows[first:])
        return dict(result='PASS',classification='injected loss with latched zero watchdog cascade',
                    legacy_result='FAIL',legacy_failed_check='platform_no_unexpected_fault',
                    gateway_expiry_wall_s=expiry,first_recorded_platform_stop_wall_s=delay,
                    limitation='specific expired platform freshness field not recorded; not a unique root-cause attribution')
    except (AssertionError,KeyError,TypeError,ValueError,StopIteration,OverflowError):
        return dict(result='FAIL',classification='not the narrowly reviewed injected-loss cascade')


def main():
    root=Path(sys.argv[1]);output=Path(sys.argv[2]);run=root/'run'
    if output.exists():raise ValueError('preserve previous reviews; use a new filename')
    files={'summary':run/'navigation_summary.json','engine':run/'engine.json','trace':run/'gateway_startup_trace.json',
           'original':run/'navigation_verification.json','residual':root/'post_residual.json'}
    data={k:json.loads(p.read_text()) for k,p in files.items()}
    observations=run/'engine_observations.jsonl'
    data['rows']=[json.loads(line) for line in observations.read_text().splitlines()]
    result=assess(data)
    result['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*files.values(),observations]}
    result['reviewer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if result['result']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
