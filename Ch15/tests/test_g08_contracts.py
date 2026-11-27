import sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'),str(root/'ros2_ws/src/ch15_mission'),str(root/'ros2_ws/src/ch15_adapters')]
from fault_injector import load_fixtures,new_receipt,l0_disposition
from ch15_mission.recovery import RetryBudget,outcome,reset_allowed
from ch15_mission.blackboard_context import BlackboardContext
from ch15_adapters.contracts import SafetyGate

class FaultContracts(unittest.TestCase):
    def test_fixtures(self):
        path=root/'config/g08_faults.yaml'
        f,sha=load_fixtures(path)
        self.assertEqual(len(f),10)
        a,b=new_receipt(path,'F01'),new_receipt(path,'F01')
        self.assertNotEqual(a['run_id'],b['run_id'])
        self.assertEqual(a['fixture_sha256'],sha)
        self.assertFalse(a['injection_observed'])
        self.assertEqual(a['result'],'NOT_RUN')
    def test_l0_f02_f05_f08_f09_f10(self):
        for fault,kw,expected in [('F02',dict(obstacle=True),'BLOCK_OR_REPLAN'),('F05',dict(ik_available=False),'BLOCKED'),('F08',dict(attitude_valid=False),'BLOCKED'),('F09',dict(battery_pct=19.9),'ABORTED'),('F10',dict(clock_valid=False),'BLOCKED')]:
            self.assertEqual(l0_disposition(fault,**kw),expected)
            self.assertEqual(l0_disposition(fault),'NO_FAULT')
        self.assertEqual(l0_disposition('F09',battery_pct=20),'NO_FAULT')
        self.assertEqual(l0_disposition('F09',battery_pct=float('nan')),'ABORTED')
    def test_heartbeat_latch_no_auto_resume(self):
        g=SafetyGate()
        self.assertTrue(g.blocked(1,True,True))
        g.heartbeat(False,1)
        self.assertFalse(g.blocked(1.1,True,True))
        self.assertTrue(g.blocked(1.151,True,True))
        self.assertTrue(g.latched)
        g.heartbeat(False,1.16)
        self.assertTrue(g.blocked(1.17,True,True))
        self.assertFalse(g.reset(1.17,True,True,False))
        self.assertTrue(g.latched)
    def test_clock_pause_rewind(self):
        c=BlackboardContext('fixture',0)
        self.assertTrue(c.clock(10_000_000_000,1))
        self.assertFalse(c.clock(10_000_000_000,1.21))
        self.assertFalse(c.clock(9_000_000_000,1.22))
        self.assertFalse(c.clock(11_000_000_000,1.23))
        self.assertIsNone(c.snapshot)
    def test_retry_prepare_budget(self):
        r=RetryBudget()
        for i in range(3):
            self.assertTrue(r.begin(safe=True,previous_terminal=True))
            self.assertFalse(r.prepare(safe=True,settled=True,fresh=False,previous_terminal=True))
            self.assertEqual(r.attempts,i+1)
        self.assertTrue(r.aborted)
        self.assertFalse(r.begin(safe=True,previous_terminal=True))
    def test_retry_original_verification(self):
        r=RetryBudget()
        self.assertTrue(r.begin(safe=True,previous_terminal=True))
        self.assertTrue(r.prepare(safe=True,settled=True,fresh=True,previous_terminal=True))
        self.assertEqual(r.resolve(safe=True,terminal=True,original_verified=False,recovery_success=True),'RETRY')
        self.assertFalse(r.finished)
        self.assertTrue(r.begin(safe=True,previous_terminal=True))
        self.assertTrue(r.prepare(safe=True,settled=True,fresh=True,previous_terminal=True))
        self.assertEqual(r.resolve(safe=True,terminal=True,original_verified=True),'SUCCESS')
        self.assertEqual(r.attempts,2)
    def test_retry_terminal_or_latch(self):
        for safe,term in [(False,True),(True,False)]:
            r=RetryBudget()
            self.assertTrue(r.begin(safe=True,previous_terminal=True))
            self.assertTrue(r.prepare(safe=True,settled=True,fresh=True,previous_terminal=True))
            self.assertEqual(r.resolve(safe=safe,terminal=term,original_verified=True),'ABORT')
            self.assertFalse(r.begin(safe=True,previous_terminal=True))
            self.assertEqual(r.attempts,1)
        self.assertEqual(outcome(True,False,False),'ERROR')
        self.assertFalse(reset_allowed(False,True,True,True,False))
    def test_retry_validation(self):
        for n in (0,4,True,3.0):
            with self.assertRaises(ValueError):RetryBudget(n)
        r=RetryBudget()
        self.assertFalse(r.begin(safe=True,previous_terminal=False))
        self.assertEqual(r.attempts,0)
if __name__=='__main__':unittest.main()
