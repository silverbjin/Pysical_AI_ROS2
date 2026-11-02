"""A validated camera capture and a detected task point have separate cadences."""
import hashlib,json,time,unittest
from unittest.mock import Mock
import numpy as np,rclpy
from sensor_msgs.msg import Image,CameraInfo
from ch13_navigation_reuse.vision_approach import VisionObserver
class CaptureHealthTests(unittest.TestCase):
 def setUp(self):
  rclpy.init();self.n=VisionObserver();self.n.health.publish=Mock();self.wall=time.monotonic();self.stamp=2_000_000_000;self.n.clock_ns=self.stamp;self.n.clock_wall=self.wall;self.n.transforms[self.stamp]=np.eye(4)
 def fill(self,wall,corrupt=False):
  rgb=Image();rgb.encoding='rgb8';rgb.step=960;rgb.data=bytes([200,20,20])*320*240
  depth=Image();depth.encoding='32FC1';depth.step=1280;depth.data=np.ones((240,320),dtype='<f4').tobytes()
  info=CameraInfo();info.k=[100.,0.,159.5,0.,100.,119.5,0.,0.,1.]
  meta={'capture_ns':self.stamp,'capture_wall':wall,'rgb_sha256':'bad' if corrupt else hashlib.sha256(bytes(rgb.data)).hexdigest()}
  for kind,payload in [('rgb',rgb),('depth',depth),('camera_info',info),('camera_meta',meta)]:self.n.cache.insert(kind,self.stamp,self.wall,'source_'+kind,payload)
  self.n.last_processed=self.stamp # inference cap is busy; no new task point is invented
 def test_capture_health_does_not_wait_for_point_inference_or_renew_duplicates(self):
  self.fill(self.wall);self.n.tick();self.n.health.publish.assert_called_once();m=json.loads(self.n.health.publish.call_args.args[0].data);self.assertEqual(m['capture_wall'],self.wall);self.assertEqual(m['capture_ns'],self.stamp);self.assertEqual(self.n.rows,[]);self.n.tick();self.n.health.publish.assert_called_once()
 def test_old_or_corrupt_capture_cannot_refresh_health(self):
  self.fill(self.wall-.31);self.n.tick();self.n.health.publish.assert_not_called();self.n.cache.frames.clear();self.fill(self.wall,corrupt=True);self.n.tick();self.n.health.publish.assert_not_called()
 def tearDown(self):self.n.destroy_node();rclpy.try_shutdown()
