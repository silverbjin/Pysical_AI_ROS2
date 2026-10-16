"""Deterministic bounded reactive exploration; no full-coverage claim."""
from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class ScanSummary:
    valid: bool
    front: float
    left: float
    right: float
    nearest: float


def summarize_scan(ranges, angle_min, angle_increment, range_min, range_max):
    bad = ScanSummary(False, 0, 0, 0, 0)
    if (not ranges or not all(math.isfinite(v) for v in
            (angle_min, angle_increment, range_min, range_max)) or angle_increment == 0
            or not 0 <= range_min < range_max or len(ranges) < 8):
        return bad
    step = abs(angle_increment)
    if step > math.pi/8:
        return bad
    angles = []
    front, left, right, distances = [], [], [], []
    for i, r in enumerate(ranges):
        a = math.atan2(math.sin(angle_min+i*angle_increment), math.cos(angle_min+i*angle_increment))
        if r == math.inf:
            d = range_max  # no hit within range, not a NaN/unknown measurement
        elif math.isfinite(r) and 0 < r and range_min <= r <= range_max:
            d = float(r)
        else:
            return bad
        angles.append(a)
        distances.append(d)
        if abs(a) <= math.pi/6 + 1e-7:
            front.append(d)
        if math.pi/6 <= a <= 5*math.pi/6:
            left.append(d)
        if -5*math.pi/6 <= a <= -math.pi/6:
            right.append(d)
    angles.sort()
    gaps = [b-a for a,b in zip(angles, angles[1:])] + [2*math.pi+angles[0]-angles[-1]]
    if max(gaps) > 1.5*step+1e-6 or not front or not left or not right:
        return bad
    return ScanSummary(True, min(front), min(left), min(right), min(distances))


class CommandWatchdog:
    def __init__(self, timeout=.5):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Invalid command timeout')
        self.timeout = timeout
        self.stamp = None
        self.command = (0,0,0)

    def receive(self, command, now):
        self.stamp = now
        self.command = tuple(command) if all(math.isfinite(v) for v in command) else (0,0,0)

    def fresh(self, now):
        return self.stamp is not None and 0 <= now-self.stamp <= self.timeout

    def value(self, now):
        return self.command if self.fresh(now) else (0,0,0)


class ExplorerCore:
    def __init__(self, seed=42, duration=300.0, linear_speed=.05, angular_speed=.15,
                 obstacle_distance=.9, clear_distance=1.05, turn_clearance=.5):
        values = (duration, linear_speed, angular_speed, obstacle_distance, clear_distance, turn_clearance)
        if (not all(math.isfinite(v) and v > 0 for v in values)
                or linear_speed > .1 or angular_speed > .3
                or clear_distance <= obstacle_distance or turn_clearance >= obstacle_distance):
            raise ValueError('Invalid exploration parameters or unsafe teaching speed')
        self.rng = random.Random(seed)
        self.duration, self.linear_speed, self.angular_speed = duration, linear_speed, angular_speed
        self.obstacle_distance, self.clear_distance, self.turn_clearance = obstacle_distance, clear_distance, turn_clearance
        self.state, self.reason = 'WAITING', 'startup'
        self.started = None
        self.progress = None
        self.turn_started = None
        self.turn_attempts = 0

    def start_turn(self, now, scan, pose):
        if scan.nearest <= self.turn_clearance or self.turn_attempts >= 4:
            self.state, self.reason = 'BLOCKED', 'turn_clearance_or_repeated_turns'
            return (0,0)
        self.direction = (1 if scan.left > scan.right else -1) if abs(scan.left-scan.right) > .1 else self.rng.choice((-1,1))
        self.target_angle = self.rng.uniform(.6, 1.2)
        self.turn_yaw, self.turn_started = pose[2], now
        self.turn_attempts += 1
        self.state, self.reason = 'TURN', 'obstacle_or_no_progress'
        return (0,0)  # stop for one control tick before turning

    def step(self, now, ready, scan, pose):
        if self.state in ('FINISHED','BLOCKED'):
            return (0,0)
        if self.started is not None and now-self.started >= self.duration:
            self.state, self.reason = 'FINISHED', 'time_budget_exhausted_partial_map'
            return (0,0)
        if not ready or scan is None or not scan.valid:
            self.state, self.reason = 'WAITING', 'inputs_not_ready'
            self.progress = None
            return (0,0)
        if scan.nearest <= self.turn_clearance:
            self.state, self.reason = 'BLOCKED', 'body_swept_clearance'
            return (0,0)
        if self.started is None:
            self.started = now
        if self.progress is None:
            self.progress = (now, pose[0], pose[1])
        if self.state == 'WAITING':
            self.state, self.reason = 'FORWARD', 'ready'
        if self.state == 'TURN':
            if scan.nearest <= self.turn_clearance:
                self.state, self.reason = 'BLOCKED', 'swept_radius_obstacle'
                return (0,0)
            delta = math.atan2(math.sin(pose[2]-self.turn_yaw), math.cos(pose[2]-self.turn_yaw))
            if self.direction*delta >= self.target_angle:
                self.state = 'FORWARD'
                self.progress = (now, pose[0], pose[1])
                if scan.front < self.clear_distance:
                    return self.start_turn(now, scan, pose)
                return (0,0)
            if now-self.turn_started >= 12:
                self.state, self.reason = 'BLOCKED', 'turn_no_yaw_progress'
                return (0,0)
            return (0, self.direction*self.angular_speed)
        t, x, y = self.progress
        moved = math.hypot(pose[0]-x, pose[1]-y)
        if moved >= .10:
            self.progress = (now, pose[0], pose[1])
            self.turn_attempts = 0
        if scan.front < self.obstacle_distance or (now-t >= 8 and moved < .05):
            return self.start_turn(now, scan, pose)
        return (self.linear_speed, 0)
