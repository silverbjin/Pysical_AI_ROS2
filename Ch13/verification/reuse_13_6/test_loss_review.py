import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from review_loss import assess


def fixture():return json.loads(Path(__file__).with_name('raw_loss_v13_fixture.json').read_text())


def test_real_injected_loss_stops_and_latches_but_preserves_legacy_failure():
    data=fixture();before=copy.deepcopy(data)
    assert assess(data)['result']=='PASS'
    assert data==before and data['original']['result']=='FAIL'


@pytest.mark.parametrize('change',[
    lambda d:d['summary'].update(case='free'),
    lambda d:d['summary'].update(injection=''),
    lambda d:d['summary'].update(no_auto_resume_after_raw_return=False),
    lambda d:d['summary']['gateway_last']['counts'].update(raw=2),
    lambda d:d['engine'].update(final_fault='CONTROL_TIMER_GAP'),
    lambda d:d['original']['checks'].update(zero_command=False),
    lambda d:d['residual'].update(result='FAIL'),
    lambda d:d['trace']['fault'].update(clock_receipt_wall=0.),
    lambda d:d['rows'][0].update(fault='INPUT_OR_CLOCK_TIMEOUT',mode='FAULT'),
    lambda d:d['rows'][-1].update(vx=.01),
    lambda d:d['rows'][-1].update(mode='ARMED'),
])
def test_classification_cannot_hide_unrelated_failure(change):
    data=fixture();change(data)
    assert assess(data)['result']=='FAIL'
