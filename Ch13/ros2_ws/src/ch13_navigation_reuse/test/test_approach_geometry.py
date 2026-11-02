from pathlib import Path
import importlib.util,sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
@unittest.skipUnless(importlib.util.find_spec('mujoco'),'requires actual model')
class ApproachGeometryTests(unittest.TestCase):
 def model(self):
  from ch13_navigation_reuse.scene import make_model
  return make_model(Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision')
 def test_actual_mount_ik_accepts_fk_point_and_rejects_unreachable(self):
  import mujoco
  from ch13_navigation_reuse.approach_geometry import tcp,position_ik
  m=self.model();d=mujoco.MjData(m);q=m.key_qpos[m.key('home').id].copy();d.qpos[:]=q;mujoco.mj_forward(m,d);target=tcp(m,d);answer=position_ik(m,q,target);self.assertIsNotNone(answer);self.assertLess(answer['residual_m'],.001);self.assertIsNone(position_ik(m,q,np.array([10.,0.,.5])))
 def test_map_collision_rejects_occupied_footprint(self):
  from ch13_navigation_reuse.approach_geometry import footprint_clear
  grid={'width':20,'height':20,'resolution':.1,'origin':[-1.,-1.],'data':[0]*400};grid['data'][10*20+10]=100;fp=[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]
  self.assertFalse(footprint_clear([0.,0.,0.],grid,fp));self.assertTrue(footprint_clear([.6,.6,0.],grid,fp))
