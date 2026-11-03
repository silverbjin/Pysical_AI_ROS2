from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.scheduler import SteadyScheduler
class SchedulerTests(unittest.TestCase):
 def test_absolute_clock_step_cannot_create_multisecond_sleep(self):
  steady=iter([10.,10.001]);wall=iter([100.,95.]);slept=[];s=SteadyScheduler(.002,monotonic=lambda:next(steady),wall=lambda:next(wall),sleeper=slept.append)
  start=s.time();elapsed=s.time()-start;s.sleep(.002-elapsed);self.assertLessEqual(max(slept),.002);self.assertEqual(len(s.events),1)
 def test_unbounded_sleep_request_is_rejected(self):
  s=SteadyScheduler(.002,sleeper=lambda _:None)
  with self.assertRaises(ValueError):s.sleep(4.6)
