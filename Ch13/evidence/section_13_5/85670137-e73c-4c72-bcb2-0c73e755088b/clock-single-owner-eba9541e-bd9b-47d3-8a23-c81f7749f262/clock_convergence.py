"""Read-only pre-admission convergence, separate from original clock preflight."""
class ClockConvergence:
    def __init__(self,*,deadline_ns=180_000_000_000):
        if type(deadline_ns) is not int or deadline_ns<40_000_000_000:raise ValueError('invalid read-only wait budget')
        self.deadline_ns=deadline_ns
        self.state='WAITING';self.started=None;self.stable_since=None
        self.previous=None;self.reason='';self.last_ratio=None
    def observe(self,raw_ns,mono_ns,real_ns,tick):
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
            good=(tick==10000 and .999<=self.last_ratio<=1.001
                  and raw_ns-p_raw<=2_000_000_000
                  and abs((real_ns-mono_ns)-(p_real-p_mono))<=1_000_000)
        if not good:self.stable_since=None;self.state='WAITING'
        elif self.stable_since is None:self.stable_since=raw_ns
        elif raw_ns-self.stable_since>=40_000_000_000:self.state='READY'
        self.previous=(raw_ns,mono_ns,real_ns)
        return self.state
