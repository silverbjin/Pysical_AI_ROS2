from pathlib import Path
import sys,importlib.util,subprocess,time,threading,json,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy
 from rclpy.node import Node
 from rclpy.executors import SingleThreadedExecutor
 from std_msgs.msg import String
 from std_srvs.srv import Trigger
 from geometry_msgs.msg import TwistStamped,TransformStamped
 from sensor_msgs.msg import LaserScan
 from tf2_msgs.msg import TFMessage
 from rosgraph_msgs.msg import Clock
 from ch13_navigation_reuse.navigation_boundary import NavigationBoundary
 from ch13_navigation_reuse.command_gateway import N,set_stamp,ns
@unittest.skipUnless(ROS,'requires actual Jazzy DDS')
class NavigationWireTests(unittest.TestCase):
 def setUp(self):
  self.relay=subprocess.Popen([__import__('ament_index_python.packages',fromlist=['get_package_prefix']).get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  rclpy.init();self.b=NavigationBoundary();self.n=Node('reuse_navigation_wire_probe');self.ns=2_000_000_000;self.nav_on=True;self.scan_on=True;self.vision_on=False;self.status={};self.outputs=[];self.nav_stamps=[]
  self.cp=self.n.create_publisher(Clock,'/clock',1);self.np=self.n.create_publisher(TwistStamped,N+'/nav_cmd',1);self.sp=self.n.create_publisher(TwistStamped,N+'/smoothed_cmd',1);self.lp=self.n.create_publisher(LaserScan,N+'/scan',1);self.tp=self.n.create_publisher(TFMessage,'/tf',1);self.hp=self.n.create_publisher(String,N+'/vision/health',1)
  self.n.create_subscription(TwistStamped,N+'/cmd_vel_raw',lambda m:self.outputs.append(m),10);self.n.create_subscription(String,N+'/navigation/status',lambda m:setattr(self,'status',json.loads(m.data)),10)
  self.n.create_timer(.02,self.send);self.ex=SingleThreadedExecutor();self.ex.add_node(self.b);self.ex.add_node(self.n);self.t=threading.Thread(target=self.ex.spin);self.t.start()
 def send(self):
  self.ns+=20_000_000;c=Clock();set_stamp(c.clock,self.ns);self.cp.publish(c)
  if self.nav_on:
   m=TwistStamped();set_stamp(m.header.stamp,self.ns);m.header.frame_id='reuse/nav_base';m.twist.linear.x=.15;self.np.publish(m);self.nav_stamps.append(self.ns)
  m=TwistStamped();set_stamp(m.header.stamp,self.ns+5_000_000);m.twist.linear.x=.1;self.sp.publish(m)
  if self.scan_on:
   m=LaserScan();set_stamp(m.header.stamp,self.ns);m.header.frame_id='reuse/scan';m.ranges=[1.]*181;self.lp.publish(m)
  transforms=[]
  for parent,child in [('reuse/map','reuse/odom'),('reuse/odom','reuse/nav_base'),('reuse/nav_base','reuse/base')]:
   t=TransformStamped();set_stamp(t.header.stamp,self.ns);t.header.frame_id=parent;t.child_frame_id=child;t.transform.rotation.w=1.;transforms.append(t)
  self.tp.publish(TFMessage(transforms=transforms))
  if self.vision_on:self.hp.publish(String(data=json.dumps({'capture_ns':self.ns,'capture_wall':time.monotonic()})))
 def until(self,predicate,timeout=3.):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   if predicate():return True
   time.sleep(.01)
  return False
 def active(self):
  self.assertTrue(self.until(lambda:self.b.c.g._fresh(time.monotonic()) and self.b.c.frames_ready()))
  client=self.n.create_client(Trigger,N+'/navigation/enable');self.assertTrue(client.wait_for_service(timeout_sec=2.));f=client.call_async(Trigger.Request());self.assertTrue(self.until(f.done));self.assertTrue(f.result().success)
  self.assertTrue(self.until(lambda:self.status.get('phase')=='ACTIVE'))
 def fault(self):
  self.assertTrue(self.until(lambda:self.status.get('phase')=='FAULT'));self.assertTrue(self.until(lambda:self.outputs[-1].twist.linear.x==0.))
 def test_smoother_output_keeps_controller_stamp(self):
  self.active();self.assertTrue(self.until(lambda:self.outputs and self.outputs[-1].twist.linear.x>.05));self.assertIn(ns(self.outputs[-1].header.stamp),self.nav_stamps)
 def test_controller_loss_cannot_be_hidden_by_smoother(self):
  self.active();self.nav_on=False;self.fault();self.nav_on=True;time.sleep(.12);self.fault()
 def test_scan_loss_latches(self):
  self.active();self.scan_on=False;self.fault();self.scan_on=True;time.sleep(.12);self.fault()
 def test_duplicate_tf_edge_faults(self):
  self.active();extra=self.n.create_publisher(TFMessage,'/tf',1);t=TransformStamped();t.header.frame_id='reuse/map';t.child_frame_id='reuse/odom';t.transform.rotation.w=1.
  end=time.monotonic()+1.
  while self.status.get('phase')!='FAULT' and time.monotonic()<end:extra.publish(TFMessage(transforms=[t]));time.sleep(.02)
  self.fault();self.assertTrue(self.status['fault'].startswith('TF_EDGE_OWNER:'));self.n.destroy_publisher(extra)
 def test_future_tf_times_out_without_being_admitted(self):
  self.active();t=TransformStamped();set_stamp(t.header.stamp,self.ns+1_000_000_000);t.header.frame_id='reuse/nav_base';t.child_frame_id='reuse/base';t.transform.rotation.w=1.;self.tp.publish(TFMessage(transforms=[t]));self.fault();self.assertIn('future',self.status['fault'].lower())
 def vision_lease(self):
  self.vision_on=True;self.assertTrue(self.until(lambda:self.b.vision.valid(self.b.c.g.clock_ns,time.monotonic())))
  client=self.n.create_client(Trigger,N+'/navigation/require_vision');self.assertTrue(client.wait_for_service(timeout_sec=2.));f=client.call_async(Trigger.Request());self.assertTrue(self.until(f.done));self.assertTrue(f.result().success)
 def test_vision_loss_stops_and_latches_after_return(self):
  self.vision_lease();self.active();self.vision_on=False;self.fault();self.vision_on=True;time.sleep(.12);self.fault()
 def test_duplicate_vision_health_owner_stops(self):
  self.vision_lease();self.active();extra=self.n.create_publisher(String,N+'/vision/health',1);self.fault();self.n.destroy_publisher(extra)
 def tearDown(self):
  self.ex.shutdown(timeout_sec=2.);self.t.join(2.);self.n.destroy_node();self.b.destroy_node();rclpy.shutdown();self.relay.terminate();self.relay.wait(timeout=3.);self.assertFalse(self.t.is_alive())
