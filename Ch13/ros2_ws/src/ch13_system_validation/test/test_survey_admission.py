import copy
import pytest


def snapshot():
    return dict(boundary=dict(phase='ACTIVE',output_held=True,vx=0.,wz=0.),
        gateway=dict(mode='ARMED',fault='',pending_future_count=0,decision_wall=10.,ready_for_arm=False,
                     source_receipts={key:dict(receipt_wall=10.) for key in ('raw','base','joints')}),
        platform=dict(mode='ARMED',fault='',stationary_ready=True))


def test_survey_continuation_requires_explicit_opt_in_and_preserves_legacy_gate():
    from ch13_navigation_reuse.nav_contract import prepared_zero
    state=snapshot()
    assert not prepared_zero(state,now=10.01)
    assert prepared_zero(state,already_armed=True,now=10.01)
    state['gateway']['ready_for_arm']=True
    assert prepared_zero(state,now=10.01)


@pytest.mark.parametrize('mutation', ['stale','future','fault','moving','pending','nonzero','partial_arm','missing'])
def test_armed_survey_never_bypasses_fresh_zero_and_actual_settling(mutation):
    from ch13_navigation_reuse.nav_contract import prepared_zero
    state=copy.deepcopy(snapshot())
    if mutation=='stale':state['gateway']['source_receipts']['raw']['receipt_wall']=9.
    if mutation=='future':state['gateway']['source_receipts']['base']['receipt_wall']=11.
    if mutation=='fault':state['gateway']['fault']='INPUT_LOSS'
    if mutation=='moving':state['platform']['stationary_ready']=False
    if mutation=='pending':state['gateway']['pending_future_count']=1
    if mutation=='nonzero':state['boundary']['vx']=.1
    if mutation=='partial_arm':state['platform']['mode']='DISARMED'
    if mutation=='missing':state['gateway']['source_receipts'].pop('joints')
    assert not prepared_zero(state,already_armed=True,now=10.01)
