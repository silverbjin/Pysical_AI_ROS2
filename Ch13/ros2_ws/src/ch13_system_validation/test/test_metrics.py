import math
import pytest
from ch13_system_validation.metrics import assess_trials


def trial(i, **kw):
    return dict(uuid=str(i), complete=True, success=True, sim_s=100., wall_s=200.,
                position_error_m=.02, max_tilt_rad=.09, cpu_percent=60., **kw)


def test_failed_trials_stay_in_denominator_and_budget_is_not_wall_time():
    rows=[trial(i) for i in range(10)]
    rows[0]['success']=False
    result=assess_trials(rows)
    assert result['result']=='PASS'
    assert result['success_rate']==.9
    assert result['mean_wall_s']==200.
    rows[1]['success']=False
    assert assess_trials(rows)['result']=='FAIL'


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'unfinished', 'nan', 'negative'])
def test_invalid_or_missing_attempt_never_becomes_pass(mutation):
    rows=[trial(i) for i in range(10)]
    if mutation=='missing':rows.pop()
    if mutation=='duplicate':rows[1]['uuid']='0'
    if mutation=='unfinished':rows[1]['complete']=False
    if mutation=='nan':rows[1]['cpu_percent']=math.nan
    if mutation=='negative':rows[1]['sim_s']=-1.
    assert assess_trials(rows)['result']=='FAIL'


@pytest.mark.parametrize('field,value', [('position_error_m',.03),('max_tilt_rad',.1),('cpu_percent',70.),('sim_s',120.01)])
def test_original_strict_metric_targets(field,value):
    rows=[trial(i) for i in range(10)]
    for row in rows:row[field]=value
    assert assess_trials(rows)['result']=='FAIL'


def test_insufficient_trials_reports_evidence_count_without_claiming_repeatability():
    result=assess_trials([trial(1)])
    assert result['result']=='FAIL'
    assert result['attempts']==1
    assert result['expected']==10
