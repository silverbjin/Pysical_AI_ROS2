"""Scenario-specific fault contract; physical stop limits remain edu_stop_v2."""
import math


def expected_source_expiry(details,control,after):
    t=details['decision_wall'];clock=details['clock_ns']
    assert math.isfinite(t) and t>=after
    assert details['control']==control and control in details['required']
    assert 0<=t-details['clock_receipt_wall']<=.30
    assert 0<=t-details['graph_wall']<=.30
    assert all(v==1 for v in details['counts'].values())
    assert all(details['counts'].get(k)==1 for k in ('clock',*details['required']))
    expected=[]
    for key in details['required']:
        sample=details['samples'][key]
        age=t-sample['receipt_wall'];stamp_age=clock-sample['stamp_ns']
        assert sample['gid'] and math.isfinite(age) and age>=0
        if age>.30:expected.append('sample_wall_expired:'+key)
        if stamp_age>300_000_000:expected.append('sample_stamp_expired:'+key)
        if key==control:assert age<=.35
    assert expected and sorted(details['failed'])==sorted(expected)
    assert set(expected)<={'sample_wall_expired:'+control,'sample_stamp_expired:'+control}
    return t


def fault_contract(summary,engine,rows):
    try:
        if summary['case']!='raw_loss':
            return engine['final_fault']=='' and all(not r['fault'] for r in rows)
        assert summary['injection']=='owned_publisher_pause_with_identity_preserved'
        injection=summary['raw_loss_injection'];after=injection['pause_sent_wall']
        assert math.isfinite(after) and after>=injection['request_wall']
        assert injection['gateway_mode']==injection['platform_mode']=='ARMED'
        assert injection['gateway_fault']==injection['platform_fault']==''
        assert summary['no_auto_resume_after_raw_return'] is True
        assert 0<summary['raw_expiry_decision_latency_s']<=.35
        gateway=summary['gateway_last']
        assert gateway['mode']=='FAULT' and gateway['fault']=='INPUT_OR_CLOCK_TIMEOUT'
        gate_time=expected_source_expiry(gateway['fault_details'],'raw',after)
        if engine['final_fault']:
            assert engine['final_fault']=='INPUT_OR_CLOCK_TIMEOUT' and engine['final_mode']=='FAULT'
            stop=expected_source_expiry(engine['fault_details'],'safe',after)
        else:
            assert all(not r['fault'] for r in rows)
            stop=gate_time+.02  # Gateway publishes its zero on the same20ms tick.
        assert rows and any(r['wall']<after and r['mode']=='ARMED' and abs(r['vx'])>0 for r in rows)
        stopped=[r for r in rows if r['wall']>=stop]
        assert stopped and all(r['vx']==r['wz']==0 for r in stopped)
        assert all(not r['fault'] for r in rows if r['wall']<after)
        assert all(math.isfinite(r[k]) for r in rows for k in ('wall','vx','wz'))
        if engine['final_fault']:
            assert all(r['mode']=='FAULT' and r['fault']==engine['final_fault'] for r in stopped)
        return True
    except (AssertionError,KeyError,TypeError,ValueError,OverflowError):
        return False
