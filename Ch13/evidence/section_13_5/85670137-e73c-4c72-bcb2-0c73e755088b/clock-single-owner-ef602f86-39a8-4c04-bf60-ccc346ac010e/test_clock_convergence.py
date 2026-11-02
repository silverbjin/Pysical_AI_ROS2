from clock_convergence import ClockConvergence

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
