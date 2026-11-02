"""Command ramps follow simulation time while watchdogs follow wall time."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.safety import Guard
class SlewClockTests(unittest.TestCase):
 def ready(self):
  g=Guard();g.clock(2_000_000_000,0);g.graph({'clock':1,'raw':1,'base':1,'joints':1},0)
  for topic in ['base','joints']:g.observe(topic,2_000_000_000,0,topic)
  g.command(2_000_000_000,0,'raw',[0]*6);self.assertTrue(g.arm(0));return g
 def test_slow_simulation_does_not_accelerate_command_per_sim_second(self):
  g=self.ready();g.clock(2_020_000_000,.20);g.command(2_020_000_000,.20,'raw',[.2,0,0,0,0,.2]);d=g.output(.20)
  self.assertAlmostEqual(d.vx,.006);self.assertAlmostEqual(d.wz,.010)
 def test_repeated_output_without_sim_progress_does_not_ramp(self):
  g=self.ready();g.command(2_010_000_000,.01,'raw',[.2,0,0,0,0,.2]);d=g.output(.02);e=g.output(.10)
  self.assertEqual(d.vx,0.);self.assertEqual(e.vx,0.);self.assertEqual(e.wz,0.)
 def test_wall_pause_still_latches(self):
  g=self.ready();g.clock(2_000_000_000,.29);d=g.output(.31);self.assertEqual(d.mode,'FAULT');self.assertEqual(d.vx,0.)
if __name__=='__main__':unittest.main()
