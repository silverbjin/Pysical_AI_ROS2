from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.nav_contract import NavigationContract
class NavContractTests(unittest.TestCase):
 def ready(self):
  c=NavigationContract();c.clock(2_000_000_000,0,'clock');c.graph({x:1 for x in ['clock','nav','smooth','scan','tf']},0)
  for a,b,g in [('reuse/map','reuse/odom','world'),('reuse/odom','reuse/nav_base','engine'),('reuse/nav_base','reuse/base','engine')]:c.tf(a,b,2_000_000_000,0,g)
  c.scan(2_000_000_000,0,'scan');self.assertTrue(c.enable(0));c.nav(2_010_000_000,.01,'nav',(.15,0,0,0,0,.1));c.smooth(2_020_000_000,.02,'smooth',(.1,0,0,0,0,.05));return c
 def test_original_nav_stamp_survives_smoother_now(self):
  c=self.ready();stamp,vx,wz,mode,fault=c.output(.03);self.assertEqual(stamp,2_010_000_000);self.assertEqual(vx,.1);self.assertEqual(mode,'ACTIVE')
 def test_controller_loss_cannot_be_refreshed_by_smoother(self):
  c=self.ready();c.output(.03);c.clock(2_100_000_000,.31,'clock');c.smooth(2_100_000_000,.31,'smooth',(.1,0,0,0,0,0));self.assertEqual(c.output(.32)[3],'FAULT')
 def test_same_edge_second_owner_faults_but_other_edges_allow_other_owners(self):
  c=self.ready();c.tf('reuse/map','reuse/odom',0,.02,'second');self.assertEqual(c.output(.03)[3],'FAULT')
 def test_fault_never_auto_resumes(self):
  c=self.ready();c.output(.03);c.output(.4);self.assertFalse(c.enable(.41));self.assertEqual(c.output(.42)[1],0.)
 def test_idle_is_explicit_generated_zero(self):
  c=self.ready();c.output(.03);c.idle();self.assertEqual(c.output(.04)[1:4],(0.,0.,'IDLE'))
