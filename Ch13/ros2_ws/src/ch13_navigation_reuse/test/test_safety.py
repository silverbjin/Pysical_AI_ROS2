from pathlib import Path
import sys,unittest,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.safety import Guard
class SafetyTests(unittest.TestCase):
    def ready(self):
        g=Guard();g.clock(2_000_000_000,0);g.graph({'clock':1,'raw':1,'base':1,'joints':1},0)
        g.observe('base',2_000_000_000,0,'base');g.observe('joints',2_000_000_000,0,'joints');g.command(2_000_000_000,0,'raw',[0]*6)
        self.assertTrue(g.arm(0));return g
    def test_duplicate_stamp_keeps_first_receipt(self):
        g=self.ready();g.command(2_000_000_000,.1,'raw',[0]*6);self.assertEqual(g.samples['raw'][1],0)
    def test_disarmed_cannot_forward_velocity(self):
        g=Guard();g.clock(2_000_000_000,0);g.command(2_000_000_000,0,'raw',[.2,0,0,0,0,.2]);self.assertEqual(g.output(.1).vx,0)
    def test_velocity_caps_and_acceleration(self):
        g=self.ready();g.clock(2_020_000_000,.02);g.command(2_020_000_000,.02,'raw',[1,0,0,0,0,1]);d=g.output(.1)
        self.assertAlmostEqual(d.vx,.03);self.assertAlmostEqual(d.wz,.05);self.assertEqual(d.stamp_ns,2_020_000_000)
    def test_expiry_latches_and_returning_input_cannot_resume(self):
        g=self.ready();g.output(.31);self.assertEqual(g.mode,'FAULT')
        g.clock(2_100_000_000,.32);g.command(2_100_000_000,.32,'raw',[.2,0,0,0,0,0]);self.assertEqual(g.output(.32).vx,0);self.assertFalse(g.arm(.32))
    def test_duplicate_publishers_latch(self):
        g=self.ready();g.graph({'clock':1,'raw':2,'base':1,'joints':1},.01);self.assertEqual(g.output(.02).mode,'FAULT')
    def test_gid_replacement_latches(self):
        g=self.ready();g.command(2_010_000_000,.01,'replacement',[0]*6);self.assertEqual(g.mode,'FAULT')
    def test_future_and_old_source_rejected(self):
        for stamp in [3_000_000_000,1_000_000_000]:
            g=self.ready();g.command(stamp,.01,'raw',[0]*6);self.assertEqual(g.mode,'FAULT')
    def test_nonfinite_and_unsupported_axes_rejected(self):
        for values in [[float('nan'),0,0,0,0,0],[0,.01,0,0,0,0],[0,0,0,.1,0,0]]:
            g=self.ready();g.command(2_010_000_000,.01,'raw',values);self.assertEqual(g.mode,'FAULT')
    def test_wrong_frame_rejected(self):
        g=self.ready();g.command(2_010_000_000,.01,'raw',[0]*6,'map');self.assertEqual(g.mode,'FAULT')
    def test_clock_rollback_latches(self):
        g=self.ready();g.clock(1_900_000_000,.01);self.assertEqual(g.mode,'FAULT')
    def test_pause_cannot_be_refreshed_with_duplicate_clock(self):
        g=self.ready();g.clock(2_000_000_000,.29);self.assertEqual(g.output(.31).mode,'FAULT')
    def test_nonfinite_state_latches(self):
        g=self.ready();g.observe('base',2_010_000_000,.01,'base',False);self.assertEqual(g.mode,'FAULT')
    def test_rearm_requires_reset_new_observations_and_zero(self):
        g=self.ready();g.clock(1_000_000_000,.01);g.reset();self.assertFalse(g.arm(.02))
    def test_state_reorder_latches(self):
        g=self.ready();g.observe('base',1_999_000_000,.01,'base');self.assertEqual(g.mode,'FAULT')
if __name__=='__main__':unittest.main()
