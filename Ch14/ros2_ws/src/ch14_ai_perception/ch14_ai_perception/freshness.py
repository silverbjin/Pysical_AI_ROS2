"""ROS stamp validity and independent wall-clock pause watchdog."""
class Freshness:
    def __init__(self,sim_time=False,max_age_ns=300_000_000,pause_ns=500_000_000):
        self.sim_time=sim_time;self.max_age_ns=max_age_ns;self.pause_ns=pause_ns
        self.epoch=0;self.last_clock=None;self.last_progress=None;self.last_input=0
    def invalidate(self):
        self.epoch+=1
    def observe(self,now,wall):
        reset=self.last_clock is not None and now<self.last_clock
        if reset:
            self.invalidate();self.last_input=0
        if self.last_clock is None or now!=self.last_clock:self.last_progress=wall
        self.last_clock=now
        return reset
    def check(self,stamp,now,wall,epoch):
        self.observe(now,wall)
        if epoch!=self.epoch:return "EPOCH_INVALID"
        if stamp<=0 or now<=0:return "CLOCK_OR_STAMP_INVALID"
        if stamp>now:return "FUTURE"
        if now-stamp>self.max_age_ns:return "STALE"
        if self.sim_time and wall-self.last_progress>=self.pause_ns:return "CLOCK_PAUSED"
        return None
    def accept(self,stamp,now,wall):
        reason=self.check(stamp,now,wall,self.epoch)
        if reason is None and stamp<=self.last_input:reason="OUT_OF_ORDER"
        if reason is None:self.last_input=stamp
        return reason
