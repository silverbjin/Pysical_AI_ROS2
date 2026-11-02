from pathlib import Path
import importlib.util,sys,subprocess,unittest
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy
 from rclpy.node import Node
 from std_srvs.srv import Trigger
@unittest.skipUnless(ROS,'requires Jazzy')
class ProcessCleanupTests(unittest.TestCase):
 def test_gateway_sigterm_has_normal_exit(self):
  p=subprocess.Popen([sys.executable,'-m','ch13_navigation_reuse.command_gateway'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  rclpy.init();n=Node('reuse_shutdown_probe')
  try:
   client=n.create_client(Trigger,'/ch13/reuse/gateway/arm');self.assertTrue(client.wait_for_service(timeout_sec=5.))
   p.terminate();self.assertEqual(p.wait(timeout=3.),0)
  finally:
   if p.poll() is None:p.kill();p.wait(timeout=3.)
   n.destroy_node();rclpy.shutdown()
@unittest.skipUnless(ROS,'requires Jazzy')
class StartupStampTests(unittest.TestCase):
 def test_no_unstamped_startup_command_before_engine_clock(self):
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from ch13_navigation_reuse.command_gateway import CommandGateway
  from geometry_msgs.msg import TwistStamped
  import time
  rclpy.init();g=CommandGateway();n=Node('unstamped_command_probe');seen=[]
  n.create_subscription(TwistStamped,'/ch13/reuse/cmd_vel_safe',lambda m:seen.append(m),1)
  try:
   end=time.monotonic()+.5
   while time.monotonic()<end:rclpy.spin_once(g,timeout_sec=.01);rclpy.spin_once(n,timeout_sec=.01)
   self.assertFalse(seen,'no source clock means no valid stamped command')
  finally:g.destroy_node();n.destroy_node();rclpy.shutdown()
if __name__=='__main__':unittest.main()

