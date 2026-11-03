import copy
import pytest
from ch13_navigation_reuse.safety import Guard
from ch13_manipulation_reuse.navigation_acceptance import fault_contract


def guard(required=('safe',),control='safe'):
    g=Guard(required,control);g.clock(1_000_000_000,10.)
    g.graph(dict.fromkeys(('clock',)+required,1),10.)
    for key in required:g.observe(key,1_000_000_000,10.,key)
    assert g.arm(10.)
    g.clock(1_200_000_000,10.31);g.graph(dict.fromkeys(('clock',)+required,1),10.31)
    for key in required:
        if key!=control:g.observe(key,1_200_000_000,10.31,key)
    assert g.output(10.31).fault=='INPUT_OR_CLOCK_TIMEOUT'
    return g


def test_first_expired_source_is_recorded_without_changing_decision_or_ttl():
    g=guard()
    assert g.fault_details['failed']==['sample_wall_expired:safe']
    assert g.fault_details['samples']['safe']['receipt_wall']==10.
    first=copy.deepcopy(g.fault_details)
    g.output(20.)
    assert g.fault_details==first and g.timeout_s==.30
    g.reset();assert g.fault_details is None


def data():
    platform=guard();gateway=guard(('raw','base','joints'),'raw')
    summary=dict(case='raw_loss',injection='owned_publisher_pause_with_identity_preserved',
                 raw_loss_injection=dict(request_wall=10.01,pause_sent_wall=10.011,
                     gateway_mode='ARMED',gateway_fault='',platform_mode='ARMED',platform_fault=''),
                 no_auto_resume_after_raw_return=True,raw_expiry_decision_latency_s=.31,
                 gateway_last=dict(mode='FAULT',fault='INPUT_OR_CLOCK_TIMEOUT',fault_details=gateway.fault_details))
    engine=dict(final_fault='INPUT_OR_CLOCK_TIMEOUT',final_mode='FAULT',fault_details=platform.fault_details)
    rows=[dict(wall=10.,vx=.1,wz=0.,mode='ARMED',fault=''),
          dict(wall=10.32,vx=0.,wz=0.,mode='FAULT',fault='INPUT_OR_CLOCK_TIMEOUT'),
          dict(wall=10.5,vx=0.,wz=0.,mode='FAULT',fault='INPUT_OR_CLOCK_TIMEOUT')]
    return summary,engine,rows


def test_expected_source_loss_is_formal_success_and_normal_timeout_is_failure():
    s,e,r=data();assert fault_contract(s,e,r)
    s['case']='free';assert not fault_contract(s,e,r)
    assert fault_contract(dict(case='free'),dict(final_fault=''),[])


def test_gateway_alone_can_stop_without_platform_fault_but_history_cannot_be_erased():
    s,e,r=data();e.update(final_fault='',fault_details=None)
    assert not fault_contract(s,e,r)
    for row in r:row.update(fault='',mode='ARMED')
    assert fault_contract(s,e,r)


@pytest.mark.parametrize('change',[
    lambda s,e,r:e.update(fault_details=None),
    lambda s,e,r:e.update(final_fault='CONTROL_TIMER_GAP'),
    lambda s,e,r:e['fault_details'].update(failed=['clock_wall_expired']),
    lambda s,e,r:e['fault_details'].update(failed=['graph_wall_expired']),
    lambda s,e,r:e['fault_details'].update(failed=['owner_count:safe']),
    lambda s,e,r:e['fault_details'].update(decision_wall=9.9),
    lambda s,e,r:s['raw_loss_injection'].update(platform_fault='INPUT_OR_CLOCK_TIMEOUT'),
    lambda s,e,r:s.update(no_auto_resume_after_raw_return=False),
    lambda s,e,r:s['gateway_last']['fault_details'].update(failed=['sample_wall_expired:base']),
    lambda s,e,r:r[-1].update(vx=.1),
    lambda s,e,r:e['fault_details']['samples']['safe'].update(receipt_wall=10.30),
])
def test_unrelated_or_unproven_fault_never_passes(change):
    s,e,r=data();change(s,e,r);assert not fault_contract(s,e,r)
