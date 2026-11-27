import math

def valid_pose(frame,p,q):
    return frame=='map' and len(p)==3 and len(q)==4 and all(math.isfinite(x) for x in (*p,*q)) and abs(sum(x*x for x in q)-1.)<=1e-6

def valid_timeout(value):
    return type(value) in (float,int) and math.isfinite(value) and 0<value<=10.

class ReadinessGate:
    def __init__(self): self.count=0
    def sample(self,missing):
        self.count=0 if missing else min(3,self.count+1)
        return self.count==3

class SafetyGate:
    def __init__(self): self.last=None; self.latched=False; self.stop=True
    def heartbeat(self,stop,now):
        if self.last is not None and now-self.last>.15: self.latched=True
        self.last=now; self.stop=stop
        if stop: self.latched=True
    def blocked(self,now,ready,owner):
        if self.last is not None and now-self.last>.15: self.latched=True
        return self.last is None or self.latched or self.stop or not ready or not owner
    def reset(self,now,ready,stopped,terminal_idle):
        if not (ready and stopped and terminal_idle and self.last is not None and now-self.last<=.15 and not self.stop): return False
        self.latched=False; return True
