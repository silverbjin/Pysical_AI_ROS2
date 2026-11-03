from pathlib import Path
import importlib.util,sys,unittest
import numpy as np
root=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(root/'Ch13/ros2_ws/src/integrated_robot_vision'))
from ch13_navigation_reuse.vision_geometry import FrameCache,admissible,red_point,manipulation_ready
class VisionGeometryTests(unittest.TestCase):
 def test_axial_depth_is_deprojected_with_13_4_geometry(self):
  rgb=np.full((240,320,3),255,dtype=np.uint8);rgb[112:128,152:168]=[220,20,20];depth=np.full((240,320),2.,dtype=np.float32)
  point,box=red_point(rgb,depth,[100.,100.,159.5,119.5]);np.testing.assert_allclose(point,[0.,0.,2.]);self.assertGreater(box.width,0)
 def test_no_color_target_is_not_scene_truth(self):
  with self.assertRaises(ValueError):red_point(np.full((240,320,3),255,dtype=np.uint8),np.ones((240,320)),[100,100,159.5,119.5])
 def test_capture_and_past_tf_limits(self):
  self.assertTrue(admissible(2_000_000_000,1.,2_200_000_000,1.2,1_950_000_000))
  self.assertFalse(admissible(2_000_000_000,1.,2_400_000_000,1.2,2_000_000_000))
  self.assertFalse(admissible(2_000_000_000,1.,2_100_000_000,1.2,1_890_000_000))
  self.assertFalse(admissible(2_000_000_000,1.,2_100_000_000,1.31,2_000_000_000))
 def test_duplicate_capture_does_not_renew_first_receipt(self):
  cache=FrameCache();cache.insert('rgb',2_000_000_000,1.,'gid','old');cache.insert('rgb',2_000_000_000,1.29,'gid','repeat');self.assertEqual(cache.frames[2_000_000_000]['rgb'],('old',1.))
 def test_camera_owner_replacement_latches(self):
  cache=FrameCache();cache.insert('rgb',2_000_000_000,1.,'gid','old')
  with self.assertRaises(ValueError):cache.insert('rgb',2_100_000_000,1.1,'other','new')
  self.assertTrue(cache.fault)
 def test_cancel_ack_or_unsettled_pose_never_ready(self):
  self.assertFalse(manipulation_ready(5,.01,.01,True,True,False));self.assertFalse(manipulation_ready(4,.01,.01,False,True,False));self.assertFalse(manipulation_ready(4,.01,.01,True,False,False));self.assertTrue(manipulation_ready(4,.05,.05,True,True,False))
@unittest.skipUnless(importlib.util.find_spec('mujoco'),'requires MuJoCo')
class ActualCameraTests(unittest.TestCase):
 def test_rendered_rgbd_deprojects_to_visible_target_surface(self):
  import mujoco
  from ch13_navigation_reuse.scene import make_model
  source=root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml';m=make_model(source,'vision');d=mujoco.MjData(m);d.qpos[:]=m.key_qpos[m.key('home').id];mujoco.mj_forward(m,d)
  import tempfile
  from ch13_navigation_reuse.sensors import SensorSuite
  temp=tempfile.TemporaryDirectory();suite=SensorSuite(m,d,'vision',temp.name)
  try:
   import time,os
   self.assertNotEqual(suite.camera.worker_pid,os.getpid())
   q=d.qpos.copy();capture_wall=time.monotonic();suite.request_capture(q,2_000_000_000,capture_wall);q[0]=.2
   rgb,depth,meta=suite.get_capture(2_000_000_000,3.);self.assertEqual(meta['capture_ns'],2_000_000_000);self.assertEqual(meta['capture_wall'],capture_wall);f=240/(2*np.tan(np.deg2rad(55)/2));point,_=red_point(rgb,depth,[f,f,159.5,119.5]);cam=m.camera('reuse_rgbd').id;world=d.cam_xpos[cam]+d.cam_xmat[cam].reshape(3,3)@np.diag([1.,-1.,-1.])@point;np.testing.assert_allclose(world,[1.75,0.,.55],atol=.025)
  finally:joined=suite.close();temp.cleanup();self.assertTrue(joined)
