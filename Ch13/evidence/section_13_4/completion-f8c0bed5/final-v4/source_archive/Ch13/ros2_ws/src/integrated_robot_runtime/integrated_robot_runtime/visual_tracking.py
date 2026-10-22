"""Thread-safe session lease; a late action result never revives a session."""
from threading import RLock


class VisualTrackingGuard:
    CONDITIONS = frozenset(('active', 'arm_safe', 'joints_fresh', 'target_valid',
                            'target_fresh', 'model_ready', 'camera_ready', 'legs_standing',
                            'arm_free', 'no_external_producer', 'action_ready', 'clock_valid'))

    def __init__(self):
        self.lock = RLock()
        self.enabled = False
        self.generation = 0
        self.outstanding = None
        self.fault = ''
        self.reason = 'default off'

    @property
    def arm_available(self):
        with self.lock:
            return not self.enabled and self.outstanding is None and not self.fault

    def enable(self, conditions):
        with self.lock:
            if (not self.arm_available or set(conditions) != self.CONDITIONS
                    or not all(conditions.values())):
                raise ValueError('tracking requires every safety gate and an unreserved arm')
            self.generation += 1
            self.enabled = True
            self.reason = 'enabled explicitly'
            return self.generation

    def reserve(self, token):
        with self.lock:
            if not self.enabled or token != self.generation or self.outstanding is not None:
                return False
            self.outstanding = token
            return True

    def complete(self, token):
        with self.lock:
            if self.outstanding == token:
                self.outstanding = None

    def disable(self, reason):
        with self.lock:
            self.enabled = False
            self.generation += 1
            self.reason = reason

    def latch_fault(self, reason):
        with self.lock:
            self.disable(reason)
            self.fault = reason

    def recover(self, *, acknowledged):
        with self.lock:
            if not acknowledged or self.enabled or self.outstanding is not None:
                return False
            self.fault = ''
            return True
