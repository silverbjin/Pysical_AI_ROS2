from pathlib import Path
import sys,unittest,importlib.util
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
M=importlib.util.find_spec('mujoco') is not None
@unittest.skipUnless(M,'requires pinned MuJoCo')
class SceneTests(unittest.TestCase):
 def test_scene_keeps_robot_masses_joints_and_actuator_caps(self):
  import mujoco,numpy as np
  from ch13_navigation_reuse.scene import make_model
  up=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml';original=mujoco.MjModel.from_xml_path(str(up));m=make_model(up,'obstacle')
  self.assertEqual(m.nq,original.nq);np.testing.assert_array_equal(m.body_mass,original.body_mass);np.testing.assert_array_equal(m.actuator_ctrlrange,original.actuator_ctrlrange);np.testing.assert_array_equal(m.jnt_range,original.jnt_range)
 def test_scan_is_real_ray_hit_not_map_lookup(self):
  import mujoco,numpy as np
  from ch13_navigation_reuse.scene import make_model,ray_scan
  up=Path(__file__).resolve().parents[5].parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml';m=make_model(up,'obstacle');d=mujoco.MjData(m);d.qpos[:]=m.key_qpos[m.key('home').id];mujoco.mj_forward(m,d)
  rays=ray_scan(m,d);self.assertAlmostEqual(rays[len(rays)//2],1.2-.14-.4,places=3)
