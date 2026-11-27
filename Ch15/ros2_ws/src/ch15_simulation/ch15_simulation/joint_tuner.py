"""C19: atomic validated gain snapshot for an independent simulation trial."""
from dataclasses import dataclass
from contextlib import contextmanager
import math

@dataclass(frozen=True)
class Gains:
    kp:float
    kd:float

def finite_number(value):
    return type(value) in (int,float) and math.isfinite(value)

class RealTimeTuner:
    def __init__(self,params=None):
        self._gains=self.validate({'kp':25.,'kd':9.5} if params is None else params)
        self.active=False

    @staticmethod
    def validate(params):
        if not isinstance(params,dict) or set(params)!={'kp','kd'}:
            raise ValueError('exact kp,kd required')
        kp,kd=params['kp'],params['kd']
        if not finite_number(kp) or not finite_number(kd) or not 0<=kp<=60 or not 0<=kd<=20:
            raise ValueError('invalid gains')
        return Gains(float(kp),float(kd))

    @property
    def snapshot(self):
        return self._gains

    def configure(self,params):
        if self.active:
            raise RuntimeError('trial active')
        candidate=self.validate(params)
        self._gains=candidate
        return candidate

    @contextmanager
    def trial(self):
        if self.active:
            raise RuntimeError('trial active')
        self.active=True
        try:
            yield self.snapshot
        finally:
            self.active=False

def torque(gains,q,qd,ref=1.):
    if not all(finite_number(v) for v in (q,qd,ref)):
        raise ValueError('nonfinite controller input')
    requested=gains.kp*(ref-q)-gains.kd*qd
    return requested,max(-60.,min(60.,requested))
