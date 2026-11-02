from pathlib import Path
import importlib.util,sys,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy
 from rclpy.parameter import Parameter
 from std_srvs.srv import Trigger
 from ch13_navigation_reuse.platform_adapter import Platform
@unittest.skipUnless(ROS,'requires Jazzy')
class FreshServiceTests(unittest.TestCase):
 def setUp(self):
  rclpy.init();self.p=Platform();self.p.stationary_ready=True;self.p.guard.mode='ARMED';self.p.last_capture_wall=time.monotonic()-.31
 def tearDown(self):self.p.destroy_node();rclpy.shutdown()
 def test_cached_settled_flag_cannot_authorize_shutdown(self):
  self.assertFalse(self.p.on_shutdown(Trigger.Request(),Trigger.Response()).success)
 def test_cached_settled_flag_cannot_authorize_arm_target(self):
  result=self.p.on_parameters([Parameter('arm_joint1_offset',value=.02)]);self.assertFalse(result.successful)
 def test_fresh_settled_zero_can_shutdown(self):
  self.p.last_capture_wall=time.monotonic();self.assertTrue(self.p.on_shutdown(Trigger.Request(),Trigger.Response()).success)
if __name__=='__main__':unittest.main()
