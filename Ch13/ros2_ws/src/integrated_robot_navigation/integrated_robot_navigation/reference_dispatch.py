"""One coalesced wake: fixed 50Hz wall phase and unmodified ROS progress.

Caller serializes this mailbox with its inbox lock. This class grants no
motion or ACK; the sole model owner must revalidate all original contracts.
"""


class ReferenceDispatch:
    period_ns=20_000_000

    def __init__(self):
        self.last_decision=None
        self.next_due_wall_ns=None
        self.waiting=self.notified=False
        self.issues=self.notifications=0

    def allowed(self,ros_ns,wall_ns):
        if self.last_decision is None:return ros_ns>0 and wall_ns>=0
        return (ros_ns>self.last_decision[0]
            and wall_ns>=self.next_due_wall_ns)

    def issued(self,ros_ns,wall_ns):
        """Commit the published reference's original decision clocks.

        Maintain the nominal phase, skipping missed slots without banked work.
        Original trajectory deltas still bound the one step actually executed.
        The application deadline remains anchored at the actual publication.
        """
        if not self.allowed(ros_ns,wall_ns):raise ValueError('reference dispatch rate/clock')
        due=(wall_ns if self.next_due_wall_ns is None else self.next_due_wall_ns)+self.period_ns
        if due<=wall_ns:
            due+=(1+(wall_ns-due)//self.period_ns)*self.period_ns
        self.next_due_wall_ns=due
        self.last_decision=(ros_ns,wall_ns);self.issues+=1;self.cancel()

    def defer(self):self.waiting=True

    def notify(self,ros_ns,wall_ns):
        if not self.waiting or self.notified or not self.allowed(ros_ns,wall_ns):return False
        self.notified=True;self.notifications+=1
        return True

    def take_notification(self):
        ready=self.notified
        if ready:self.cancel()
        return ready

    def begin_tick(self):self.cancel()

    def cancel(self):self.waiting=self.notified=False

    def snapshot(self):
        return dict(scope='wall_reference_decision_phase_not_application_deadline',
            clock_rule='positive_original_ros_progress_no_extrapolation',
            last_decision=self.last_decision,next_due_wall_ns=self.next_due_wall_ns,
            waiting=self.waiting,notified=self.notified,
            period_ns=self.period_ns,issues=self.issues,notifications=self.notifications)
