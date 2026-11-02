"""Actual safe-command DDS ingress to platform; scripted clock, no physics."""
from pathlib import Path
import importlib.util,subprocess,sys,time,threading,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy
 from rclpy.node import Node
 from rclpy.executors import SingleThreadedExecutor
 from geometry_msgs.msg import TwistStamped
 from rosgraph_msgs.msg import Clock
 from std_srvs.srv import Trigger
 from ch13_navigation_reuse.platform_adapter import Platform
 from ch13_navigation_reuse.command_gateway import N,set_stamp
@unittest.skipUnless(ROS,'requires Jazzy DDS')
class PlatformWireTests(unittest.TestCase):
 def setUp(self):
  self.relay=subprocess.Popen([__import__('ament_index_python.packages',fromlist=['get_package_prefix']).get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  rclpy.init();self.p=Platform();self.n=Node('reuse_safe_wire_probe');self.ns=2_000_000_000;self.sending=True;self.paused=False;self.vx=0.;self.decision=None
  self.pub=self.n.create_publisher(TwistStamped,N+'/cmd_vel_safe',1)
  self.n.create_timer(.02,self.send);self.ex=SingleThreadedExecutor();self.ex.add_node(self.p);self.ex.add_node(self.n);self.thread=threading.Thread(target=self.ex.spin);self.thread.start()
 def send(self):
  if not self.paused:self.ns+=20_000_000
  self.decision,_=self.p.engine_command(self.ns);c=Clock();set_stamp(c.clock,self.ns);self.p.clock_pub.publish(c)
  if self.sending:
   m=TwistStamped();set_stamp(m.header.stamp,self.ns);m.header.frame_id='reuse/nav_base';m.twist.linear.x=self.vx;self.pub.publish(m)
 def until(self,predicate,timeout=2.):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if predicate():return True
   time.sleep(.01)
  return False
 def arm(self):
  self.assertTrue(self.until(lambda:self.p.guard._fresh(time.monotonic()),3.))
  client=self.n.create_client(Trigger,N+'/platform/arm');self.assertTrue(client.wait_for_service(timeout_sec=2.));f=client.call_async(Trigger.Request());self.assertTrue(self.until(f.done));self.assertTrue(f.result().success,f.result().message)
 def fault(self,reason=None):
  self.assertTrue(self.until(lambda:self.p.guard.mode=='FAULT'));self.assertTrue(self.until(lambda:self.decision is not None and self.decision.vx==0.))
  if reason:self.assertEqual(self.p.guard.fault,reason)
 def test_safe_loss_latches_after_return(self):
  self.arm();self.vx=.15;self.assertTrue(self.until(lambda:self.decision.vx>.03));self.sending=False;self.fault();self.sending=True;time.sleep(.12);self.fault()
 def test_safe_duplicate_publisher_faults(self):
  self.arm();extra=self.n.create_publisher(TwistStamped,N+'/cmd_vel_safe',1);self.fault('DUPLICATE_OWNER:safe');self.n.destroy_publisher(extra)
 def test_safe_replacement_uses_sample_gid(self):
  self.arm();self.sending=False;self.n.destroy_publisher(self.pub);self.pub=self.n.create_publisher(TwistStamped,N+'/cmd_vel_safe',1);self.sending=True;self.fault('OWNER_REPLACED:safe')
 def test_engine_clock_pause_latches(self):
  self.arm();self.paused=True;self.fault();self.paused=False;time.sleep(.12);self.fault()
 def tearDown(self):
  self.ex.shutdown(timeout_sec=2.);self.thread.join(2.);self.n.destroy_node();self.p.destroy_node();rclpy.shutdown();self.relay.terminate();self.relay.wait(timeout=3.);self.assertFalse(self.thread.is_alive())
if __name__=='__main__':unittest.main()
