from pathlib import Path
import importlib.util,sys,time,json,unittest
root=Path(__file__).resolve().parents[5];sys.path.insert(0,str(root/'Ch13/scripts/reuse_13_5'))
@unittest.skipUnless(importlib.util.find_spec('rclpy'),'requires DDS')
class VisionAdmissionTests(unittest.TestCase):
 def test_admission_waits_for_new_capture_after_planning(self):
  import rclpy
  from rclpy.node import Node
  from std_msgs.msg import String
  from vision_mission import wait_new_capture
  rclpy.init();node=Node('reuse_fresh_admission_probe');start=time.monotonic();state={'capture_ns':2_000_000_000,'capture_wall':start,'tf_stamp_ns':2_000_000_000};clock=[2_010_000_000];counter=[0];pub=node.create_publisher(String,'/ch13/reuse/test_admission',1)
  def receive(m):state.clear();state.update(json.loads(m.data))
  node.create_subscription(String,'/ch13/reuse/test_admission',receive,1)
  def send():
   if time.monotonic()-start<.12:return
   counter[0]+=1;stamp=2_000_000_000+counter[0]*20_000_000;clock[0]=stamp+10_000_000;pub.publish(String(data=json.dumps({'capture_ns':stamp,'capture_wall':time.monotonic(),'tf_stamp_ns':stamp})))
  node.create_timer(.02,send)
  def until(predicate,timeout):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    rclpy.spin_once(node,timeout_sec=.01)
    if predicate():return True
   return False
  try:
   observation=wait_new_capture(until,lambda:state,lambda:clock[0]);self.assertGreater(observation['capture_ns'],2_000_000_000);self.assertGreaterEqual(time.monotonic()-start,.12)
  finally:node.destroy_node();rclpy.shutdown()
