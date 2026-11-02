"""150s original clock witness: actual rate, uncertainty and real closure."""
import importlib
import importlib.util
from pathlib import Path
import pytest

def api():
    name='integrated_robot_navigation.clock_witness'
    assert importlib.util.find_spec(name) is not None,'continuous measured-rate witness missing'
    return importlib.import_module(name).assess_measured_clock_witness

def records(rate=1.,correction_ppm=-4.967865):
    yield dict(kind='metadata',uid=1000,pid=100,adjtimex_modes=0,
        writes_system_settings=False,raw_duration_ns=150_000_000_000)
    for i in range(1501):
        raw=10_000_000_000+i*100_000_000
        mono=20_000_000_000+round(i*100_000_000*rate)
        yield dict(raw_before_ns=raw,raw_after_ns=raw+100,monotonic_ns=mono,
            realtime_ns=mono+10**18,modes=0,errno=0,state=0,tick_us=9999,
            freq_scaled_ppm=round((100+correction_ppm)*65536))
    yield dict(kind='finished',raw_elapsed_ns=150_000_001_000,writes_system_settings=False)

def test_measured_five_ppm_is_not_an_eight_percent_drift_or_time_step():
    result=api()(records(rate=.999995032135))
    assert result['passed'] and result['windows']>1000
    assert result['minimum_lower_ratio']>=.999 and result['maximum_upper_ratio']<=1.001
    assert result['maximum_history_samples']<=512
    assert result['declared_duration_ns']==150_000_000_000
    assert result['scope']=='continuous_original_clock_witness_not_engine_acceptance'

@pytest.mark.parametrize('rate',[.917,1.083,.998,1.002])
def test_actual_slow_or_fast_clock_cannot_hide_in_metadata(rate):
    assert not api()(records(rate,correction_ppm=0.))['passed']

@pytest.mark.parametrize('mutation',['real_step','mono_rollback','raw_rollback','uncertainty',
    'gap','missing_metadata','missing_finish','early_finish','declared_duration','writes',
    'partial_window','unknown_tick','noninteger','post_finish'])
def test_broken_or_incomplete_original_witness_is_rejected(mutation):
    rows=list(records());row=rows[40]
    if mutation=='real_step':row['realtime_ns']+=1_000_001
    elif mutation=='mono_rollback':row['monotonic_ns']=rows[39]['monotonic_ns']-1
    elif mutation=='raw_rollback':row['raw_before_ns']=rows[39]['raw_after_ns']-1
    elif mutation=='uncertainty':row['raw_after_ns']+=5_000_000
    elif mutation=='gap':del rows[30:65]
    elif mutation=='missing_metadata':rows.pop(0)
    elif mutation=='missing_finish':rows.pop()
    elif mutation=='early_finish':rows[-1]['raw_elapsed_ns']=149_999_999_999
    elif mutation=='declared_duration':rows[0]['raw_duration_ns']=149_000_000_000
    elif mutation=='writes':rows[0]['writes_system_settings']=True
    elif mutation=='partial_window':rows=rows[:100]+rows[-1:]
    elif mutation=='unknown_tick':row['tick_us']=9345
    elif mutation=='noninteger':row['raw_after_ns']=float(row['raw_after_ns'])
    elif mutation=='post_finish':rows.append(rows[1])
    assert not api()(iter(rows))['passed'],mutation

def test_new_mode_requires_explicit_existing_read_only_profile_and_keeps_default():
    path=Path(__file__).resolve().parents[5]/'.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/native_engine_plan.py'
    spec=importlib.util.spec_from_file_location('clock_witness_test_plan',path)
    plan=importlib.util.module_from_spec(spec);spec.loader.exec_module(plan)
    assert hasattr(plan,'clock_witness_mode'),'new witness flag is not bound explicitly'
    assert plan.clock_witness_mode([])=='legacy'
    assert plan.clock_witness_mode(['--service-only','--compensated-tick-read-only'])=='legacy'
    assert plan.clock_witness_mode(['--service-only','--compensated-tick-read-only','--measured-clock-witness'])=='measured_rate'
    with pytest.raises(ValueError):plan.clock_witness_mode(['--measured-clock-witness'])
