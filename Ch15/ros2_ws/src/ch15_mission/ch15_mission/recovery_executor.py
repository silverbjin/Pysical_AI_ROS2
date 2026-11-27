"""G08 opt-in MOCK executor; the accepted G03/G05 executor is unchanged.
No recovery movement, no safety reset or fault-latch override.
"""
import time
import rclpy
from .mission_executor import MissionExecutor,ST
from .recovery import RetryBudget

class RecoveryExecutor(MissionExecutor):
    def __init__(self):
        super().__init__()
        self.search_budget=RetryBudget(3)
        self.pick_budget=RetryBudget(3)

    def safe(self):
        return self.fresh_ready() and not self.fault and not any(s.latched for s in self.sup.values()) and self.bb.clock_valid

    def begin_attempt(self,budget,task,step,now):
        if not self.safe() or not self.all_terminal():
            self.trigger_fault('retry_unsafe_or_unresolved')
            return False
        if not self.stopped() or self.gait!='stand' or now-self.gait_at>.3:
            return False
        if not budget.begin(safe=True,previous_terminal=True):
            self.trigger_fault(step+'_budget_exhausted')
            return False
        self.bb.mark_settled()
        task['deadline']=now+1.2
        self.emit('RECOVERY_ATTEMPT',step=step,attempt=budget.attempts,previous_terminal=True,settled=True,zero_samples=self.zero_count,settle_ns=self.bb.settle_ns)
        return True

    def prepare(self,budget,task,step,now):
        target=self.bb.read(now,self.tf_ready())
        safe=self.safe()
        settled=self.stopped() and self.gait=='stand' and now-self.gait_at<=.3
        terminal=self.all_terminal()
        if not safe or not terminal:
            self.trigger_fault('retry_unsafe_or_unresolved')
            return False
        if target is not None and settled:
            if not budget.prepare(safe=safe,settled=settled,fresh=True,previous_terminal=terminal):
                self.trigger_fault('retry_preparation_rejected')
                return False
            self.emit('RECOVERY_PREPARED',step=step,attempt=budget.attempts,stamp_ns=target.stamp_ns,settle_ns=self.bb.settle_ns,previous_terminal=terminal,settled=settled,fresh=True)
            return True
        if now>=task['deadline']:
            budget.prepare(safe=safe,settled=settled,fresh=False,previous_terminal=terminal)
            self.emit('RECOVERY_MISS',step=step,attempt=budget.attempts,reason=self.bb.reason)
            if budget.aborted:self.trigger_fault(step+'_budget_exhausted')
        return False

    def step(self,name):
        if name not in ('detect','pick_retract','approach_stand'):
            return super().step(name)
        now=time.monotonic()
        if now-self.entered[name]>8.:
            self.trigger_fault(name+'_deadline')
            return ST.FAILURE
        if not self.safe():
            self.trigger_fault('recovery_not_safe')
            return ST.FAILURE
        task=self.tasks[name]
        if name=='approach_stand':
            # The inherited step requires stand, observed zero, then a newer target.
            return super().step(name)
        budget=self.search_budget if name=='detect' else self.pick_budget
        if budget.aborted:return ST.FAILURE
        if not budget.active:
            self.begin_attempt(budget,task,name,now)
            return ST.RUNNING if not self.fault else ST.FAILURE
        if not budget.prepared:
            if not self.prepare(budget,task,name,now):
                return ST.RUNNING if not self.fault else ST.FAILURE
        if name=='detect':
            # Actual validated observation, not a synthetic recovery success.
            outcome=budget.resolve(safe=self.safe(),terminal=self.all_terminal(),original_verified=True)
            self.emit('RECOVERY_RESULT',step=name,attempt=budget.attempts,outcome=outcome)
            return self.done(name) if outcome=='SUCCESS' else ST.FAILURE
        # One exact Pick UUID per prepared attempt. Inherited admission/witness.
        result=self.action(name,'pick')
        if name not in self.requests:
            if result==ST.FAILURE:self.trigger_fault('pick_target_invalid')
            return result
        s,rid=self.requests[name]
        a=s.rows[rid]
        if a.state=='ABORTED' and a.resolved and a.terminal_status==6:
            decision=budget.resolve(safe=self.safe(),terminal=self.all_terminal(),original_verified=False)
            self.emit('RECOVERY_RESULT',step=name,attempt=budget.attempts,outcome=decision,prior_uuid=a.accepted_uuid,terminal_status=6)
            del self.requests[name]
            self.bb.invalidate('fresh_after_failed_pick_required')
            if decision=='ABORT':
                self.trigger_fault('pick_retry_exhausted')
                return ST.FAILURE
            return ST.RUNNING
        if result==ST.SUCCESS:
            decision=budget.resolve(safe=self.safe(),terminal=self.all_terminal(),original_verified=self.valid_witness(a.accepted_uuid,'pick'))
            self.emit('RECOVERY_RESULT',step=name,attempt=budget.attempts,outcome=decision,prior_uuid=a.accepted_uuid,terminal_status=a.terminal_status)
            if decision!='SUCCESS':
                self.trigger_fault('pick_unverified');return ST.FAILURE
            return ST.SUCCESS
        if result==ST.FAILURE:
            self.trigger_fault('pick_nonretryable')
        return result

    def reset(self,req,res):
        super().reset(req,res)
        if res.success:
            self.search_budget=RetryBudget(3)
            self.pick_budget=RetryBudget(3)
        return res

def main():
    rclpy.init();n=RecoveryExecutor()
    try:rclpy.spin(n)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        clean=n.all_terminal() and (not n.started or n.finished)
        n.close();n.destroy_node();rclpy.try_shutdown()
    if not clean:raise SystemExit(2)
