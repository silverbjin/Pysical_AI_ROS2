from clock_convergence import ClockConvergence
import clock_convergence
import pytest


def test_compensated_nominal_encoding_is_read_only_and_not_tick_alone():
    assert hasattr(clock_convergence,'nominal_tick_encoding'), 'fractional nominal tick cannot be represented'
    nominal=clock_convergence.nominal_tick_encoding
    assert nominal(10000,0,allow_compensated=True)
    assert nominal(9999,100*65536,allow_compensated=True)
    assert not nominal(9999,100*65536), 'default strict metadata policy changed'
    assert not nominal(9999,0,allow_compensated=True), 'uncompensated tick admitted'
    assert not nominal(9166,500*65536,allow_compensated=True), 'original 8.3% clock skew admitted'
    assert not nominal(9999,103*65536,allow_compensated=True), 'special encoding exceeded 2ppm bound'
    assert not nominal(9999,None,allow_compensated=True)


def test_symmetric_upper_tick_requires_opposite_frequency_and_the_same_two_ppm_bound():
    nominal=clock_convergence.nominal_tick_encoding
    assert nominal(10001,-100*65536,allow_compensated=True)
    assert nominal(10001,-6556270,allow_compensated=True), 'actual 280ff810 compensated sample rejected'
    assert not nominal(10001,-100*65536), 'strict default changed'
    assert not nominal(10001,100*65536,allow_compensated=True), 'wrong correction sign admitted'
    assert not nominal(10001,0,allow_compensated=True)
    assert not nominal(10001,-103*65536,allow_compensated=True)
    assert not nominal(10002,-200*65536,allow_compensated=True), 'unobserved coarse encoding expanded'
    assert not nominal(10001,None,allow_compensated=True)


def test_upper_encoding_still_rejects_actual_drift_and_jumps():
    for rate,step in ((.917,0),(1.,2_000_000)):
        gate=ClockConvergence(allow_compensated_tick=True)
        for s in range(180):
            mono=int(s*10**9*rate);real=mono+10**18+(step if s%2 else 0)
            assert gate.observe(s*10**9,mono,real,10001,freq_scaled_ppm=-100*65536)=='WAITING'
        assert gate.observe(180*10**9,int(180*10**9*rate),10**18+int(180*10**9*rate),10001,
            freq_scaled_ppm=-100*65536)=='FAULT'


def test_upper_encoding_requires_the_same_full_quiet_window():
    gate=ClockConvergence(allow_compensated_tick=True)
    for s in range(41):
        assert gate.observe(s*10**9,s*10**9,s*10**9+10**18,10001,freq_scaled_ppm=-100*65536)=='WAITING'
    assert gate.observe(41*10**9,41*10**9,41*10**9+10**18,10001,freq_scaled_ppm=-100*65536)=='READY'


def test_compensated_encoding_still_requires_measured_rate_and_40_seconds():
    assert hasattr(clock_convergence,'nominal_tick_encoding'), 'read-only encoding recognition missing'
    gate=ClockConvergence(allow_compensated_tick=True)
    for s in range(41):
        assert gate.observe(s*10**9,s*10**9,s*10**9+10**18,9999,freq_scaled_ppm=100*65536)=='WAITING'
    assert gate.observe(41*10**9,41*10**9,41*10**9+10**18,9999,freq_scaled_ppm=100*65536)=='READY'


@pytest.mark.parametrize('rate,step',[(.917,0),(1.,2_000_000)])
def test_fractional_encoding_never_masks_slow_clock_or_realtime_jump(rate,step):
    assert hasattr(clock_convergence,'nominal_tick_encoding'), 'read-only encoding recognition missing'
    gate=ClockConvergence(allow_compensated_tick=True)
    for s in range(180):
        mono=int(s*10**9*rate);real=mono+10**18+(step if s%2 else 0)
        assert gate.observe(s*10**9,mono,real,9999,freq_scaled_ppm=100*65536)=='WAITING'
    assert gate.observe(180*10**9,int(180*10**9*rate),10**18+int(180*10**9*rate),9999,
        freq_scaled_ppm=100*65536)=='FAULT'

def feed(gate,seconds,*,tick=10000,rate=1.,real_step=0):
    return gate.observe(seconds*10**9,int(seconds*10**9*rate),int(seconds*10**9*rate)+10**18+real_step,tick)

def test_nominal_tick_needs_40_seconds_and_verified_original_rate():
    gate=ClockConvergence()
    for s in range(41):assert feed(gate,s)=='WAITING'
    assert feed(gate,41)=='READY'

def test_tick_without_rate_convergence_cannot_admit():
    gate=ClockConvergence()
    for s in range(180):assert feed(gate,s,rate=.917)=='WAITING'
    assert feed(gate,180,rate=.917)=='FAULT'

def test_observed_slew_then_natural_convergence_is_not_rewritten():
    gate=ClockConvergence()
    for s in range(116):assert feed(gate,s,tick=9166,rate=.917)=='WAITING'
    for s in range(116,157):assert feed(gate,s,rate=1.)=='WAITING'
    assert feed(gate,157)=='READY'

def test_real_step_restarts_quiet_without_extending_raw_deadline():
    gate=ClockConvergence()
    for s in range(40):assert feed(gate,s)=='WAITING'
    assert feed(gate,40,real_step=3_000_000_000)=='WAITING'
    for s in range(41,81):assert feed(gate,s,real_step=3_000_000_000)=='WAITING'
    assert feed(gate,81,real_step=3_000_000_000)=='READY'

def test_bad_tick_to_raw_deadline_fails_without_admitting():
    gate=ClockConvergence()
    for s in range(180):assert feed(gate,s,tick=9166)=='WAITING'
    assert feed(gate,180,tick=9166)=='FAULT'

def test_raw_backstep_is_sticky_fault():
    gate=ClockConvergence();feed(gate,10)
    assert feed(gate,9)=='FAULT'
    assert feed(gate,100)=='FAULT'

def test_explicit_read_only_wait_budget_does_not_change_default_gate_or_quiet_requirement():
    gate=ClockConvergence(deadline_ns=300_000_000_000)
    for s in range(181):assert feed(gate,s,tick=9167,rate=.917)=='WAITING'
    for s in range(181,222):assert feed(gate,s,rate=1.)=='WAITING'
    assert feed(gate,222)=='READY'
    default=ClockConvergence()
    feed(default,0,tick=9167)
    assert feed(default,180,tick=9167)=='FAULT'
