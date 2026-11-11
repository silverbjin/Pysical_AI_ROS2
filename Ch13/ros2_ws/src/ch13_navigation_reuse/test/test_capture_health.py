"""A validated camera capture and a detected task point have separate cadences."""
import hashlib,json,time,unittest
from unittest.mock import Mock,patch
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
 def test_cylinder_initialization_stays_out_of_first_frame_callback(self):
  import builtins
  import ch13_manipulation_reuse.cylinder_vision as cylinder
  original=builtins.__import__;inside=[False]
  def guarded_import(name,*args,**kwargs):
   if name=='ch13_manipulation_reuse.cylinder_vision' and inside[0]:
    raise AssertionError('cylinder initialization in frame callback')
   return original(name,*args,**kwargs)
  self.n.destroy_node()
  fit=Mock(side_effect=ValueError('cylinder controlled rejection'))
  with patch.object(cylinder,'fit_cylinder',fit),patch('builtins.__import__',side_effect=guarded_import):
   self.n=VisionObserver(target_shape='cylinder');self.n.health.publish=Mock()
   self.wall=time.monotonic();self.n.clock_ns=self.stamp;self.n.clock_wall=self.wall
   self.n.transforms[self.stamp]=np.eye(4);self.fill(self.wall);self.n.last_processed=0
   inside[0]=True;self.n.tick()
  fit.assert_called_once()
  self.assertEqual(self.n.rejected['cylinder controlled rejection'],1)
  self.n.health.publish.assert_called_once()
  health=json.loads(self.n.health.publish.call_args.args[0].data)
  self.assertEqual((health['capture_ns'],health['capture_wall']),(self.stamp,self.wall))
 def test_opt_in_observer_timing_preserves_original_health(self):
  import os
  self.n.destroy_node()
  with patch.dict(os.environ,{'CH13_CALLBACK_TIMING':'1'}):self.n=VisionObserver()
  self.n.health.publish=Mock();self.wall=time.monotonic();self.n.clock_ns=self.stamp;self.n.clock_wall=self.wall
  self.n.transforms[self.stamp]=np.eye(4);self.fill(self.wall);self.n.tick()
  health=json.loads(self.n.health.publish.call_args.args[0].data)
  self.assertEqual((health['capture_ns'],health['capture_wall']),(self.stamp,self.wall))
  trace=self.n.diagnostics()['callback_timing']
  self.assertEqual([r['name'] for r in trace['rows']],['vision.tick'])
  self.assertGreaterEqual(trace['rows'][0]['end_wall'],trace['rows'][0]['start_wall'])
 def test_level2_cadence_processes_arrived_frame_before_saved_capture_deadline(self):
  from types import SimpleNamespace
  from ch13_system_validation.scenarios import get_scenario
  from ch13_manipulation_reuse.lease import Lease
  from ch13_navigation_reuse.vision_approach import red_point
  self.n.destroy_node();self.n=VisionObserver(inference_hz=get_scenario('level2_obstacles').vision_hz)
  # Actual v48 frame was complete by8757.273662; this tick occurs at8757.280.
  clock=[8757.280];self.wall=clock[0];self.stamp=67808000000
  self.n.clock_ns=self.stamp;self.n.clock_wall=self.wall;self.n.transforms[self.stamp]=np.eye(4)
  self.fill(8757.229389063);self.n.last_processed=67796000000
  self.n.last_processed_wall=8757.212981876
  def measured_fit(*args):
   result=red_point(*args);clock[0]+=.024552201;return result
  with patch('ch13_navigation_reuse.vision_approach.time',SimpleNamespace(monotonic=lambda:clock[0])),patch('ch13_navigation_reuse.vision_approach.red_point',side_effect=measured_fit):
   self.n.tick()
  self.assertEqual(len(self.n.rows),1,'arrived frame deferred by inference cap')
  observation=self.n.rows[0]
  self.assertEqual(observation['capture_wall'],8757.229389063)
  self.assertLess(observation['inference_finished_wall'],8757.046126638+.3)
  lease=Lease('saved-deadline-component')
  self.assertTrue(lease.observe(observation,'observer',clock[0]))
  self.assertTrue(lease.observation_fresh(67820000000,8757.348507426))
 def tearDown(self):self.n.destroy_node();rclpy.try_shutdown()
