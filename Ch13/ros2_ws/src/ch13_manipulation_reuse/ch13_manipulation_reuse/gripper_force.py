"""Explicit contact-triggered force hold through the sole native position PD."""
import math


def servo_reference(nominal,position,velocity,kp,kd,effort,scale):
    if (not all(math.isfinite(x) for x in (nominal,position,velocity,kp,kd,effort,scale))
            or not 0<=nominal<=.05 or kp<=0 or kd<0 or not 0<=effort<=.5 or not 0<=scale<=1):
        raise ValueError('invalid bounded gripper force reference')
    force_reference=position+(kd*velocity-effort)/kp
    return (1-scale)*nominal+scale*force_reference


class ForceHold:
    def __init__(self):
        self.since=None;self.start=None;self.scale=0.;self.events=[]

    def update(self,sim_s,phase,nominal,effort,contacts,position,velocity,kp,kd,allowed):
        if not math.isfinite(sim_s):raise ValueError('invalid gripper force clock')
        if nominal>.002:
            if self.start is not None:self.events.append(dict(event='explicit_open',sim_s=sim_s))
            self.since=self.start=None;self.scale=0.
            return nominal
        if self.start is None:
            dual=all(math.isfinite(contacts.get(f,0.)) and contacts.get(f,0.)>.005 for f in ('link7','link8'))
            if allowed and phase=='CLOSE' and dual and position>.002:
                if self.since is None:self.since=sim_s
                if sim_s-self.since>=.25:
                    self.start=sim_s;self.events.append(dict(event='dual_contact_force_hold',sim_s=sim_s,effort_cap_N=effort))
            else:self.since=None
        if self.start is None:return nominal
        self.scale=max(self.scale,min(1.,max(0.,(sim_s-self.start)/.5)))
        return servo_reference(nominal,position,velocity,kp,kd,effort,self.scale)

    def status(self):return dict(active=self.start is not None,ready=self.scale>=1.,ramp=self.scale)
