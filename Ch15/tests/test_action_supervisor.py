import sys,pathlib,unittest
from types import SimpleNamespace as NS
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_mission'))
from ch15_mission.action_supervisor import ActionSupervisor
class Future:
    def __init__(self):self.value=None;self.complete=False
    def done(self):return self.complete
    def result(self):assert self.complete;return self.value
    def set(self,x):self.value=x;self.complete=True
class Handle:
    def __init__(self,uid,accepted=True):
        self.accepted=accepted;self.goal_id=NS(uuid=bytes.fromhex(uid));self.result=Future();self.cancel=Future();self.result_calls=0;self.cancel_calls=0
    def get_result_async(self):self.result_calls+=1;return self.result
    def cancel_goal_async(self):self.cancel_calls+=1;return self.cancel
class Client:
    def __init__(self):self.sent=[];self.handles=[]
    def server_is_ready(self):return True
    def send_goal_async(self,g,goal_uuid):
        f=Future();self.sent.append(f);self.handles.append(Handle(goal_uuid));return f
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=0.;self.c=Client();self.events=[];self.blocks=[];self.witnesses=set()
        self.s=ActionSupervisor(self.c,lambda x:x,lambda x:x in self.witnesses,lambda e,**k:self.events.append((e,k)),self.blocks.append,lambda:self.t,timeout=1.)
    def send(self):
        rid=self.s.send(object());return rid,self.c.handles[-1]
    def accept(self,h):self.c.sent[-1].set(h);self.s.tick()
    def terminal(self,h,status=4,success=True):
        h.result.set(NS(status=status,result=NS(success=success)));self.s.tick()
    def ack(self,h):
        h.cancel.set(NS(goals_canceling=[NS(goal_id=h.goal_id)]));self.s.tick()
    def test_normal_duplicate(self):
        r,h=self.send()
        with self.assertRaises(RuntimeError):self.s.send(object())
        self.accept(h);self.s.tick();self.witnesses.add(bytes(h.goal_id.uuid).hex());self.terminal(h)
        self.assertEqual(self.s.poll(r),'SUCCEEDED_VERIFIED');self.assertEqual(h.result_calls,1);self.assertEqual(len(self.c.sent),1)
    def test_rejection(self):
        r,h=self.send();h.accepted=False;self.accept(h)
        self.assertEqual(self.s.poll(r),'REJECTED');self.assertEqual(h.result_calls,0)
    def test_abort(self):
        r,h=self.send();self.accept(h);self.terminal(h,6,False);self.assertEqual(self.s.poll(r),'ABORTED')
    def test_cancel_after_accept(self):
        r,h=self.send();self.accept(h);self.s.request_cancel(r);self.s.tick();self.ack(h);self.terminal(h,5,False)
        self.assertEqual(self.s.poll(r),'CANCELED');self.assertEqual(h.cancel_calls,1)
    def test_cancel_before_accept(self):
        r,h=self.send();self.s.request_cancel(r);self.s.tick();self.accept(h);self.ack(h);self.terminal(h,5,False)
        self.assertEqual(self.s.poll(r),'CANCELED');self.assertEqual(h.cancel_calls,1);self.assertEqual(h.result_calls,1)
    def test_timeout(self):
        r,h=self.send();self.accept(h);self.t=1.01;self.s.tick();self.ack(h);self.terminal(h,5,False)
        self.assertEqual(self.s.poll(r),'CANCELED');self.assertTrue(self.blocks);self.assertTrue(self.s.rows[r].timed_out)
    def test_late_result(self):
        r,h=self.send();self.accept(h);self.s.request_cancel(r);self.s.tick();self.ack(h);self.terminal(h,5,False)
        r2,h2=self.send();self.accept(h2);h.result.set(NS(status=4,result=NS(success=True)));self.s.tick()
        self.assertEqual(self.s.poll(r),'CANCELED');self.assertEqual(self.s.poll(r2),'ACCEPTED');self.assertEqual(h.result_calls,1)
        self.terminal(h2,6,False);self.assertEqual(self.s.poll(r2),'ABORTED')
    def test_unconfirmed(self):
        r,h=self.send();self.accept(h);self.s.request_cancel(r);self.s.tick();self.t=2.01;self.s.tick()
        self.assertEqual(self.s.poll(r),'FAILED');self.assertFalse(self.s.ready_for_goal());self.assertFalse(self.s.reset())
        self.terminal(h,5,False);self.assertEqual(self.s.poll(r),'FAILED');self.assertFalse(self.s.ready_for_goal())
    def test_uuid_mismatch(self):
        r,h=self.send();h.goal_id.uuid=bytes(16);self.accept(h);self.assertTrue(self.s.latched);self.assertFalse(self.s.ready_for_goal())
    def test_missing_witness(self):
        r,h=self.send();self.accept(h);self.terminal(h);self.assertEqual(self.s.poll(r),'VERIFYING');self.t=1.01;self.s.tick();self.assertEqual(self.s.poll(r),'FAILED')
if __name__=='__main__':unittest.main()
