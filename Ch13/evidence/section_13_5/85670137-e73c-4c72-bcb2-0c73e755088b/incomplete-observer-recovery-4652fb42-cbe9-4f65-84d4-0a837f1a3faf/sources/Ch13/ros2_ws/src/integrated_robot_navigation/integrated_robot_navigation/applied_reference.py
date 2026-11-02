"""One outstanding reference; only an original physics observation grants credit."""
from collections import deque
from copy import deepcopy
import math
from .samples import sample_valid


class AppliedReferenceCredit:
    def __init__(self,names,max_age_ns=200_000_000):
        self.names=tuple(names)
        if not self.names or len(set(self.names))!=len(self.names):
            raise ValueError('invalid reference joint names')
        self.max_age_ns=max_age_ns
        self.pending=self.last_ack=self.held=None
        self.samples={};self.events=deque(maxlen=32)

    def _values(self,values):
        values=tuple(values)
        if len(values)!=len(self.names) or not all(math.isfinite(x) for x in values):
            raise ValueError('invalid reference values')
        return values

    def prime(self,held):
        if self.pending is not None:raise ValueError('outstanding reference')
        self.held=self._values(held)

    def submitted(self,values,ros_ns,wall_ns):
        values=self._values(values)
        if self.pending is not None:
            if values!=self.pending['values']:raise ValueError('outstanding reference')
            return  # A heartbeat cannot renew the original application deadline.
        if values==self.held:return
        self.pending=dict(values=values,issued_ros_ns=ros_ns,issued_wall_ns=wall_ns)
        self.held=values
        self.events.append(dict(event='submitted',**self.pending))

    def receive(self,sample):
        if sample.frame_id!='mujoco/pre_step':return
        names=tuple(sample.data['name']);values=tuple(sample.data['position'])
        if (len(names)!=len(values) or len(set(names))!=len(names)
                or not all(math.isfinite(x) for x in values)):
            raise ValueError('invalid applied observation')
        if not set(self.names).issubset(names):raise ValueError('missing applied joints')
        key=(sample.epoch,sample.sequence,sample.stamp_ns)
        previous=self.samples.get(key)
        if previous is not None:
            if previous.data!=sample.data:raise ValueError('conflicting applied observation')
            return  # Preserve the first local receipt, including duplicate ACKs.
        self.samples[key]=deepcopy(sample)
        while len(self.samples)>16:del self.samples[next(iter(self.samples))]

    def permit(self,ros_ns,wall_ns):
        if self.pending is None:return True
        pending=self.pending
        ros_age=ros_ns-pending['issued_ros_ns'];wall_age=wall_ns-pending['issued_wall_ns']
        if min(ros_age,wall_age)<0:raise ValueError('application clock rollback')
        if max(ros_age,wall_age)>self.max_age_ns:
            raise ValueError('native reference unconfirmed')
        candidates=sorted(self.samples.values(),key=lambda sample:sample.stamp_ns)
        for sample in candidates:
            valid,_=sample_valid(sample,ros_ns,wall_ns,0,max_age_ns=self.max_age_ns)
            if (not valid or sample.stamp_ns<pending['issued_ros_ns']
                    or sample.received_ns<pending['issued_wall_ns']):continue
            observed=dict(zip(sample.data['name'],sample.data['position']))
            if tuple(observed[name] for name in self.names)!=pending['values']:continue
            self.last_ack=dict(stamp_ns=sample.stamp_ns,received_ns=sample.received_ns,
                sequence=sample.sequence,issued_ros_ns=pending['issued_ros_ns'],
                issued_wall_ns=pending['issued_wall_ns'],values=pending['values'])
            self.pending=None
            self.events.append(dict(event='applied',**self.last_ack))
            return True
        return False

    def suspend(self,reason):
        if self.pending is not None:
            self.events.append(dict(event='abandoned_for_stop',reason=reason,**self.pending))
        self.pending=None

    def snapshot(self):
        return deepcopy(dict(pending=self.pending,last_ack=self.last_ack,events=list(self.events)))
