"""Canonical native observations, exact capture/receipt ownership, no commands.

Inbox methods are called under their owning node's lock/serialized callback.
This extraction preserves Task 5 receiver semantics for the crawl owner too.
"""
import math

from .projection import body_data
from .samples import Sample, SensorBundle

STREAMS = ('joints', 'imu', 'contacts', 'body', 'scan', 'carry')


def sensor_sample(key, msg, receipt, epoch):
    stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
    frame = msg.header.frame_id
    if key == 'joints':
        if len(set(msg.name)) != len(msg.name) or len(msg.position) != len(msg.name) or len(msg.velocity) != len(msg.name):
            raise ValueError('joint shape/names')
        data = dict(position=dict(zip(msg.name, msg.position)), velocity=dict(zip(msg.name, msg.velocity)))
        frame = 'base_link'  # model-named joint axes, not a Cartesian JointState header
    elif key == 'imu':
        a, w = msg.linear_acceleration, msg.angular_velocity
        data = dict(acceleration=(a.x, a.y, a.z), angular_velocity=(w.x, w.y, w.z))
    elif key == 'contacts':
        if msg.epoch != epoch:
            raise ValueError('engine epoch changed; restart required')
        data = dict(names=tuple(msg.names), points=tuple((p.x, p.y, p.z) for p in msg.points),
            forces=tuple(msg.normal_forces), touching=tuple(msg.touching), unexpected_contacts=msg.unexpected_contacts)
    elif key == 'body':
        data = body_data(msg)
    elif key == 'scan':
        if any(math.isnan(v) or v < msg.range_min or v == -math.inf for v in msg.ranges):
            raise ValueError('invalid native scan range')
        data = dict(ranges=tuple(min(v, msg.range_max) for v in msg.ranges),
            hits=tuple(math.isfinite(v) and v <= msg.range_max for v in msg.ranges),
            range_min=msg.range_min, range_max=msg.range_max,
            angle_min=msg.angle_min, angle_increment=msg.angle_increment)
    elif key == 'carry':
        data = dict(ready=msg.ready, generation=msg.generation, model_sha256=msg.model_sha256)
    else:
        raise ValueError('unknown observation stream')
    return Sample(stamp, receipt, epoch, stamp, frame, data)


class SensorInbox:
    def __init__(self, epoch):
        self.epoch = epoch
        self.clear(-1)

    def clear(self, reset_ros):
        self.cutoff = reset_ros
        self.samples = {key: None for key in STREAMS}
        self.pending = {key: {} for key in STREAMS}

    def receive(self, key, sample):
        if key not in self.pending or sample.epoch != self.epoch:
            raise ValueError('observation stream/epoch mismatch')
        previous = self.samples[key]
        if (sample.stamp_ns <= self.cutoff or
                previous is not None and sample.stamp_ns <= previous.stamp_ns):
            return
        self.pending[key].setdefault(sample.stamp_ns, sample)
        while len(self.pending[key]) > 10:
            del self.pending[key][min(self.pending[key])]

    def bundle(self, ros_ns, *, wall_ns=None):
        for key, candidates in self.pending.items():
            # Concurrent ingress may deliver a capture <= this decision's ROS
            # time AFTER its wall evaluation time. Keep that original receipt
            # pending for the next decision, not as a negative-age replacement.
            eligible = [stamp for stamp,sample in candidates.items() if stamp <= ros_ns
                        and (wall_ns is None or sample.received_ns <= wall_ns)]
            if eligible:
                latest = max(eligible)
                self.samples[key] = candidates[latest]
                for stamp in list(candidates):
                    if stamp <= latest:
                        del candidates[stamp]
        return SensorBundle(**self.samples)
