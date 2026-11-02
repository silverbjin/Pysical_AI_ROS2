"""Read-only environment admission before creating ROS command receivers.

No clock is set, published or substituted. READY describes the observed quiet
window only. Existing runtime backstep/epoch protection remains authoritative.
"""


class ClockStabilityGate:
    quiet_ns=40_000_000_000
    deadline_ns=150_000_000_000
    jump_limit_ns=1_000_000

    def __init__(self):
        self.state='WAITING';self.reason=''
        self.started=self.stable_since=self.last_wall=self.last_offset=None
        self.jumps=0

    def observe(self,wall_ns,system_ns):
        if self.state=='FAULT':return self.snapshot()
        if type(wall_ns) is not int or type(system_ns) is not int or wall_ns<0:
            self.state,self.reason='FAULT','invalid clock observation'
            return self.snapshot()
        offset=system_ns-wall_ns
        if self.started is None:
            self.started=self.stable_since=wall_ns
        elif wall_ns<self.last_wall:
            self.state,self.reason='FAULT','monotonic rollback'
            return self.snapshot()
        elif abs(offset-self.last_offset)>self.jump_limit_ns:
            self.jumps+=1;self.stable_since=wall_ns
            if self.state=='READY':
                self.state,self.reason='FAULT','system clock changed after admission'
        self.last_wall,self.last_offset=wall_ns,offset
        if self.state!='FAULT':
            if wall_ns-self.started>=self.deadline_ns:
                self.state,self.reason='FAULT','system clock stability deadline'
            elif wall_ns-self.stable_since>=self.quiet_ns:self.state='READY'
        return self.snapshot()

    def snapshot(self):
        return dict(state=self.state,reason=self.reason,jumps=self.jumps,
            started_wall_ns=self.started,stable_since_wall_ns=self.stable_since,
            last_wall_ns=self.last_wall,last_system_offset_ns=self.last_offset,
            quiet_ns=self.quiet_ns,deadline_ns=self.deadline_ns,jump_limit_ns=self.jump_limit_ns,
            scope='observed_system_clock_window_not_runtime_or_engine_acceptance')
