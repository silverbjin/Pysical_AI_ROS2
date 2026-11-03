"""Bind native camera bytes to actual C++ first receipt/GID without a second image."""
import hashlib,json,time,unittest,subprocess,threading
from pathlib import Path
import numpy as np,rclpy
from sensor_msgs.msg import Image,CameraInfo
from std_msgs.msg import String
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy
from ament_index_python.packages import get_package_prefix
from ch13_navigation_reuse.command_gateway import N,set_stamp
class CameraReceiptTests(unittest.TestCase):
 def image(self):
  m=Image();set_stamp(m.header.stamp,2_000_000_000);m.header.frame_id='reuse/camera_optical';m.width=320;m.height=240;m.encoding='rgb8';m.step=960;m.data=bytes([180,20,20])*320*240;return m
 def test_corrupt_native_bytes_never_match_and_duplicates_never_renew_receipt(self):
  from ch13_navigation_reuse.camera_native import CameraLink,canonical
  link=CameraLink();m=self.image();b=canonical('rgb',m);wall=time.monotonic();packet='|'.join(['camera1','rgb','1'*32,'a'*32,str(round(wall*1e9)),'0',hashlib.sha256(b).hexdigest(),str(len(b))]);self.assertIsNone(link.receipt(packet));bad=self.image();bad.data[0]=0;self.assertIsNone(link.native('rgb',bad));matched=link.native('rgb',m);self.assertIsNotNone(matched);self.assertAlmostEqual(matched[2]['receipt_wall'],wall,places=7);self.assertIsNone(link.receipt(packet));self.assertIsNone(link.native('rgb',m))
 def test_actual_cpp_receipt_matches_native_rgb_depth_info_and_meta(self):
  from ch13_navigation_reuse.camera_native import CameraLink
  relay=subprocess.Popen([get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);rclpy.init();node=Node('camera_receipt_fixture');link=CameraLink();matches=[];errors=[];q=QoSProfile(depth=2,reliability=ReliabilityPolicy.RELIABLE)
  def consume(result):
   if result:matches.append(result)
  def receipt(m):
   try:consume(link.receipt(m.data))
   except ValueError as exc:errors.append(str(exc))
  pubs={}
  for kind,typ,topic in [('rgb',Image,'rgb'),('depth',Image,'depth'),('camera_info',CameraInfo,'camera_info'),('camera_meta',String,'camera_capture')]:
   pubs[kind]=node.create_publisher(typ,N+'/'+topic,q);node.create_subscription(typ,N+'/'+topic,lambda m,k=kind:consume(link.native(k,m)),q)
  node.create_subscription(String,N+'/ingress/vision',receipt,16)
  def until(p,timeout):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    rclpy.spin_once(node,timeout_sec=.01)
    if p():return True
   return False
  try:
   self.assertTrue(until(lambda:all(pub.get_subscription_count()>=2 for pub in pubs.values()) and node.count_publishers(N+'/ingress/vision')==1,3.))
   rgb=self.image();depth=self.image();depth.encoding='32FC1';depth.step=1280;depth.data=np.ones((240,320),dtype='<f4').tobytes();info=CameraInfo();info.header=rgb.header;info.width=320;info.height=240;info.k=[100.,0.,159.5,0.,100.,119.5,0.,0.,1.];meta=String(data=json.dumps({'capture_ns':2_000_000_000,'capture_wall':time.monotonic(),'rgb_sha256':hashlib.sha256(bytes(rgb.data)).hexdigest()}))
   before=time.monotonic()
   for k,m in [('rgb',rgb),('depth',depth),('camera_info',info),('camera_meta',meta)]:pubs[k].publish(m)
   self.assertTrue(until(lambda:len(matches)==4 or errors,3.),str(errors));self.assertFalse(errors);self.assertEqual({x[0] for x in matches},set(pubs));self.assertTrue(all(before<=x[2]['receipt_wall']<=time.monotonic() for x in matches));self.assertTrue(all(len(x[2]['publisher_gid'])==16 for x in matches))
  finally:node.destroy_node();rclpy.try_shutdown();relay.terminate();relay.wait(timeout=3.)
