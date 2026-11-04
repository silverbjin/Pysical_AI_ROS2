"""Thread-safe step exchange and asynchronous action ownership."""
import copy
import threading
import time

STEPS=('navigate','find','pick','finish','recover','return','charge')


class TaskPort:
    def __init__(self):
        self.lock=threading.RLock()
        self.data=dict(requested=[],completed={},cancel_reason='',error='',closed=False,exit_code=None,progress={},events=[])

    def event(self,event,**values):
        with self.lock:self.data['events'].append(dict(event=event,wall=time.monotonic(),**copy.deepcopy(values)))

    def submit(self,name):
        if name not in STEPS:raise ValueError('unknown task: '+name)
        with self.lock:
            if self.data['closed'] or (self.data['cancel_reason'] and name!='charge'):return
            if name not in self.data['requested']:
                self.data['requested'].append(name);self.event('requested',task=name)

    def complete(self,name,payload):
        with self.lock:
            if name in self.data['completed']:raise ValueError('duplicate completion: '+name)
            self.data['completed'][name]=copy.deepcopy(payload);self.event('completed',task=name,payload=payload)

    def progress(self,**values):
        with self.lock:self.data['progress'].update(copy.deepcopy(values))

    def cancel(self,reason):
        with self.lock:
            if not self.data['cancel_reason']:
                self.data['cancel_reason']=str(reason);self.event('cancel_requested',reason=reason)

    def fail(self,error):
        with self.lock:
            if not self.data['error']:self.data['error']=str(error);self.event('worker_error',error=str(error))

    def close(self,code):
        with self.lock:
            self.data.update(closed=True,exit_code=code);self.event('closed',exit_code=code)

    def snapshot(self):
        with self.lock:return copy.deepcopy(self.data)


class GoalTracker:
    """Polled only by the ROS owner, including after a BT leaf is INVALID."""
    def __init__(self):
        self.rows=[];self.canceling=False;self.terminals=[];self.errors=[];self.cancel_acks=[]

    def add(self,sent):self.rows.append(dict(sent=sent,handle=None,result=None,cancel=None,done=False))
    def cancel(self):self.canceling=True

    def poll(self):
        for row in self.rows:
            try:
                cancel=row.get('cancel')
                if cancel is not None and cancel.done() and not row.get('ack_recorded'):
                    self.cancel_acks.append(bool(getattr(cancel.result(),'goals_canceling',[])))
                    row['ack_recorded']=True
                if row['done']:continue
                if row['handle'] is None:
                    if not row['sent'].done():continue
                    handle=row['sent'].result()
                    if not handle.accepted:row['done']=True;continue
                    row.update(handle=handle,result=handle.get_result_async())
                if self.canceling and row['cancel'] is None and not row['result'].done():
                    row['cancel']=row['handle'].cancel_goal_async()
                if row['result'].done():
                    self.terminals.append(row['result'].result().status);row['done']=True
            except Exception as error:
                self.errors.append(str(error));row['done']=True

    @property
    def drained(self):return all(r['done'] for r in self.rows)

    def audit(self):
        return dict(terminals=list(self.terminals),errors=list(self.errors),
            cancel_requests=sum(r['cancel'] is not None for r in self.rows),cancel_acks=list(self.cancel_acks),
            pending=sum(not r['done'] for r in self.rows))


class DeferredClients:
    """Clients stay alive until owned send/result futures have been drained."""
    def __init__(self,goals):self.goals=goals;self.finalizers=[]
    def defer(self,finalizer):self.finalizers.append(finalizer)
    def close(self,until):
        if not self.goals.drained:
            self.goals.cancel()
            if not until(lambda:self.goals.drained,5.):
                raise RuntimeError('owned action futures unresolved; clients retained')
        for finalizer in self.finalizers:finalizer()
        self.finalizers.clear()


def stop_worker(thread,port,timeout=30.):
    if not thread.is_alive():return True
    port.cancel('mission_exception')
    deadline=time.monotonic()+timeout
    while thread.is_alive() and time.monotonic()<deadline:thread.join(timeout=.05)
    return not thread.is_alive()
