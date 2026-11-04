"""ROS-independent live mission authority. Capture and first receipt never renew."""
import copy
import math


class Lease:
    timeout = .30

    def __init__(self, session):
        self.session = session
        self.phase = 'WAITING'
        self.fault = ''
        self.owners = {}
        self.observation = None
        self.observation_receipt = None
        self.message = None
        self.mission_receipt = None
        self.goal_id = None
        self.sequence = 0
        self.last_clock = None
        self.last_wall = None

    def trip(self, reason):
        if not self.fault:
            self.fault = reason
        self.phase = 'FAULT'
        return self.phase

    def owner(self, key, identity):
        if not identity:
            return self.trip('MISSING_OWNER:' + key)
        if key in self.owners and self.owners[key] != identity:
            return self.trip('OWNER_REPLACED:' + key)
        self.owners[key] = identity
        return None

    def observe(self, sample, owner, receipt):
        if self.fault or self.owner('observer', owner):
            return False
        try:
            stamp, wall, tf = sample['capture_ns'], sample['capture_wall'], sample['tf_stamp_ns']
            if (type(stamp) is not int or stamp <= 0 or type(tf) is not int
                    or not 0 <= stamp-tf <= 100_000_000
                    or not all(math.isfinite(x) for x in [wall, receipt, sample['first_receipt_wall']])
                    or not wall <= sample['first_receipt_wall'] <= receipt + .01
                    or len(sample['point']) != 3 or not all(math.isfinite(x) for x in sample['point'])
                    or not sample['source_gids'] or len(sample['rgb_sha256']) != 64):
                raise ValueError('invalid original capture')
            if self.owner('camera_sources', tuple(sorted(sample['source_gids'].items()))):
                return False
            if self.observation is not None:
                previous = self.observation['capture_ns']
                if stamp < previous:
                    return self.trip('OBSERVATION_REORDER')
                if stamp == previous:
                    if sample != self.observation:
                        return self.trip('CAPTURE_CONTENT_CHANGED')
                    return False
            self.observation = copy.deepcopy(sample)
            self.observation_receipt = receipt
            return True
        except (ValueError, TypeError, KeyError):
            self.trip('INVALID_OBSERVATION')
            return False

    def heartbeat(self, message, owner, receipt):
        if self.fault or self.phase == 'REVOKED' or self.owner('mission', owner):
            return False
        try:
            if message['session'] != self.session:
                return self.trip('SESSION_MISMATCH')
            seq = message['sequence']
            if (type(seq) is not int or seq <= 0 or type(message['stamp_ns']) is not int
                    or message['stamp_ns'] <= 0 or not math.isfinite(receipt)
                    or not isinstance(message['goal_id'], str) or not message['goal_id']
                    or message['terminal'] != 4 or message['state'] not in ('OFFER','REVOKE')
                    or len(message['target']) != 3
                    or not all(math.isfinite(x) for x in message['target'])
                    or type(message['capture_ns']) is not int
                    or message.get('task_phase','WAITING') not in ('WAITING','PRE_GRASP','GRASP_APPROACH','CLOSE','LIFT','HOLD','POST_SETTLE')):
                raise ValueError('invalid heartbeat')
            if self.goal_id is not None and message['goal_id'] != self.goal_id:
                return self.trip('GOAL_REPLACED')
            if seq <= self.sequence:
                return False  # Repetition never refreshes the watchdog.
            if self.message is not None:
                if message['target'] != self.message['target']:
                    return self.trip('GOAL_POSE_CHANGED')
                if message['stamp_ns'] < self.message['stamp_ns']:
                    return self.trip('MISSION_CLOCK_REORDER')
            self.message = copy.deepcopy(message)
            self.sequence, self.goal_id, self.mission_receipt = seq, message['goal_id'], receipt
            if message['state'] == 'REVOKE':
                self.phase = 'REVOKED'
            return True
        except (ValueError, TypeError, KeyError):
            self.trip('INVALID_HEARTBEAT')
            return False

    def begin_execution(self):
        if self.phase != 'READY':
            raise ValueError('live READY required')
        self.phase = 'EXECUTING'

    def evaluate(self, clock_ns, wall, *, settled, supported, goal_status,
                 actual_pose, navigation_idle):
        if not self.fresh(clock_ns,wall):
            return self.phase
        if self.message['capture_ns'] > self.observation['capture_ns']:
            return self.phase
        if any(g != self.goal_id and s in (1,2,3) for g,s in goal_status.items()):
            return self.trip('NEW_NAV_GOAL')
        authorized = (goal_status.get(self.goal_id) == 4 and navigation_idle and supported)
        target = self.message['target']
        pose_ok = (len(actual_pose) == 3 and all(math.isfinite(x) for x in actual_pose)
                   and math.hypot(actual_pose[0]-target[0],actual_pose[1]-target[1]) <= .10
                   and abs(math.atan2(math.sin(actual_pose[2]-target[2]),math.cos(actual_pose[2]-target[2]))) <= .10)
        if self.phase in ('READY','EXECUTING'):
            if not authorized or not pose_ok:
                return self.trip('LIVE_SUPPORT_OR_NAVIGATION_LOST')
        elif authorized and pose_ok and settled:
            self.phase = 'READY'
        return self.phase

    def fresh(self, clock_ns, wall):
        """Shared original receipt/capture watchdog; never changes authority."""
        if self.fault or self.phase == 'REVOKED':
            return False
        if self.last_clock is not None and (clock_ns < self.last_clock or wall < self.last_wall):
            self.trip('CLOCK_ROLLBACK');return False
        self.last_clock, self.last_wall = clock_ns, wall
        if self.message is None:
            return False
        if not 0 <= wall-self.mission_receipt <= self.timeout:
            self.trip('MISSION_EXPIRED');return False
        if not -25_000_000 <= clock_ns-self.message['stamp_ns'] <= 300_000_000:
            self.trip('MISSION_STAMP_EXPIRED');return False
        sample = self.observation
        if (sample is None or not 0 <= wall-sample['capture_wall'] <= self.timeout
                or not 0 <= wall-self.observation_receipt <= self.timeout
                or not -25_000_000 <= clock_ns-sample['capture_ns'] <= 300_000_000):
            self.trip('OBSERVATION_EXPIRED');return False
        return True
