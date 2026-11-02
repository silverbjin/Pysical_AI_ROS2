"""Read-only pre-admission convergence, separate from original clock preflight."""
def nominal_tick_encoding(tick,freq_scaled_ppm=None,*,allow_compensated=False):
    """Recognize the observed adjacent nominal USER_HZ=100 encodings.

    No adjtimex write. Optional 9999us/+100ppm or 10001us/-100ppm must compensate within
    2ppm; actual RAW rate/REALTIME continuity and host QPC remain mandatory.
    The default strict policy and original 10000us representation stay intact.
    """
    if type(tick) is not int:return False
    if tick==10000:return True
    return (allow_compensated is True and tick in (9999,10001)
        and type(freq_scaled_ppm) is int
        and abs(freq_scaled_ppm+(tick-10000)*100*65536)<=2*65536)


class ClockConvergence:
    def __init__(self,*,deadline_ns=180_000_000_000,allow_compensated_tick=False):
        if type(deadline_ns) is not int or deadline_ns<40_000_000_000:raise ValueError('invalid read-only wait budget')
        if type(allow_compensated_tick) is not bool:raise ValueError('explicit compensated encoding flag required')
        self.allow_compensated_tick=allow_compensated_tick
        self.deadline_ns=deadline_ns
        self.state='WAITING';self.started=None;self.stable_since=None
        self.previous=None;self.reason='';self.last_ratio=None
    def observe(self,raw_ns,mono_ns,real_ns,tick,*,freq_scaled_ppm=None):
        if self.state=='FAULT':return self.state
        if any(type(v) is not int or v<0 for v in (raw_ns,mono_ns,real_ns,tick)):
            self.state,self.reason='FAULT','invalid observation';return self.state
        if self.started is None:self.started=raw_ns
        if self.previous is not None and raw_ns<=self.previous[0]:
            self.state,self.reason='FAULT','raw clock did not advance';return self.state
        if raw_ns-self.started>=self.deadline_ns:
            self.state,self.reason='FAULT','read-only convergence deadline';return self.state
        good=False
        if self.previous is not None:
            p_raw,p_mono,p_real=self.previous
            self.last_ratio=(mono_ns-p_mono)/(raw_ns-p_raw)
            good=(nominal_tick_encoding(tick,freq_scaled_ppm,allow_compensated=self.allow_compensated_tick)
                  and .999<=self.last_ratio<=1.001
                  and raw_ns-p_raw<=2_000_000_000
                  and abs((real_ns-mono_ns)-(p_real-p_mono))<=1_000_000)
        if not good:self.stable_since=None;self.state='WAITING'
        elif self.stable_since is None:self.stable_since=raw_ns
        elif raw_ns-self.stable_since>=40_000_000_000:self.state='READY'
        self.previous=(raw_ns,mono_ns,real_ns)
        return self.state
