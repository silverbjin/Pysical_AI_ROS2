"""Non-blocking, single-owner action supervisor. One attempt, one result future.
Transport is injected for deterministic tests; runtime supplies rclpy ActionClient.
All methods run on one executor thread. Never spin or wait on a future here.
"""
from dataclasses import dataclass
from uuid import uuid4
import time

TERMINAL={'SUCCEEDED_VERIFIED','REJECTED','ABORTED','CANCELED','FAILED'}

@dataclass
class Attempt:
    request_id: str
    requested_uuid: str
    deadline: float
    sent: object = None
    handle: object = None
    result: object = None
    cancel: object = None
    cancel_at: float | None = None
    ack_read: bool = False
    state: str = 'PENDING'
    accepted_uuid: str = ''
    terminal_status: int | None = None
    resolved: bool = False
    result_read: bool = False
    timed_out: bool = False

class ActionSupervisor:
    def __init__(self,client,uuid_message,witness,emit=lambda *a,**k:None,block=lambda reason:None,now=time.monotonic,timeout=5.,cancel_budget=2.):
        self.client=client;self.uuid_message=uuid_message;self.witness=witness;self.emit=emit;self.block=block
        self.now=now;self.timeout=timeout;self.cancel_budget=cancel_budget;self.rows={};self.active=None;self.latched=False
    def ready_for_goal(self):
        return not self.latched and self.active is None and self.client.server_is_ready()
    def event(self,a,event,**kw):
        self.emit(event,request_id=a.request_id,goal_uuid=a.accepted_uuid,**kw)
    def send(self,goal):
        if not self.ready_for_goal():raise RuntimeError('goal admission blocked')
        rid=uuid4().hex;uid=uuid4().hex
        a=Attempt(rid,uid,self.now()+self.timeout);self.rows[rid]=a;self.active=rid
        self.event(a,'GOAL_SENT',requested_uuid=uid)
        try:a.sent=self.client.send_goal_async(goal,goal_uuid=self.uuid_message(uid))
        except Exception as exc:self.fail(a,'send_exception:'+str(exc),False)
        return rid
    def poll(self,request_id):return self.rows[request_id].state
    def request_cancel(self,request_id):
        a=self.rows[request_id]
        if a.resolved or a.cancel_at is not None:return
        a.cancel_at=self.now();self.block('cancel_requested');self.event(a,'CANCEL_REQUEST')
    def fail(self,a,reason,resolved=False):
        self.latched=True;self.block(reason);a.state='FAILED';a.resolved=resolved
        self.event(a,'FAULT',reason=reason)
        if resolved:self.active=None
    def finish(self,a,state):
        # A latched unresolved attempt may later resolve, but it must never
        # become successful or unlock admission without explicit reset.
        a.resolved=True
        if a.state!='FAILED':a.state=state
        if self.active==a.request_id:self.active=None
    def tick(self):
        if self.active is None:return
        a=self.rows[self.active];now=self.now()
        try:
            if a.handle is None and a.sent is not None and a.sent.done():
                h=a.sent.result();a.handle=h
                if not h.accepted:
                    self.event(a,'GOAL_REJECTED',requested_uuid=a.requested_uuid);self.finish(a,'REJECTED');return
                a.accepted_uuid=bytes(h.goal_id.uuid).hex()
                if a.accepted_uuid!=a.requested_uuid:
                    self.fail(a,'uuid_mismatch');return
                self.event(a,'GOAL_ACCEPTED')
                a.result=h.get_result_async()
                if a.state!='FAILED':a.state='ACCEPTED'
            if not a.result_read and now>=a.deadline and a.cancel_at is None and (a.result is None or not a.result.done()):
                a.timed_out=True;self.request_cancel(a.request_id)
            if a.cancel_at is not None and a.handle is not None and a.accepted_uuid==a.requested_uuid and a.cancel is None and not a.result_read:
                a.cancel=a.handle.cancel_goal_async()
            if a.cancel is not None and a.cancel.done() and not a.ack_read:
                a.ack_read=True
                ids=[bytes(x.goal_id.uuid).hex() for x in a.cancel.result().goals_canceling]
                self.event(a,'CANCEL_ACK',matches=a.accepted_uuid in ids,ids=ids)
                if a.accepted_uuid not in ids and not a.result_read:self.fail(a,'cancel_ack_mismatch')
            if a.result is not None and a.result.done() and not a.result_read:
                result=a.result.result();a.result_read=True;a.terminal_status=int(result.status)
                if a.terminal_status not in (4,5,6):
                    self.fail(a,'nonterminal_result');return
                self.event(a,'GOAL_TERMINAL',status=a.terminal_status)
                if a.terminal_status==5:self.finish(a,'CANCELED');return
                if a.terminal_status==6:self.finish(a,'ABORTED');return
                value=result.result
                success=bool(value.success) if hasattr(value,'success') else getattr(value,'error_code',None)==0
                if not success or a.cancel_at is not None:
                    self.fail(a,'terminal_without_verified_success',True);return
                a.state='VERIFYING'
            if a.state=='VERIFYING':
                if a.cancel_at is not None:self.fail(a,'canceled_during_verification',True);return
                if self.witness(a.accepted_uuid):
                    self.finish(a,'SUCCEEDED_VERIFIED');return
                if now>=a.deadline:self.fail(a,'missing_witness',True);return
            if a.cancel_at is not None and now-a.cancel_at>=self.cancel_budget and not a.resolved and a.state!='FAILED':
                self.fail(a,'cancel_terminal_unconfirmed')
        except Exception as exc:
            if a.state!='FAILED':self.fail(a,'future_exception:'+str(exc))
    def reset(self):
        if self.active is not None or any(not a.resolved for a in self.rows.values()):return False
        self.latched=False;return True
