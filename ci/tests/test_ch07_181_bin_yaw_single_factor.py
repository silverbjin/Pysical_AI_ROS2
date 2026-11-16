"""C12 only rotate one real SDF bin field; keep source scene fail-closed."""
import sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_bin_yaw_single_factor import rotate_bin
from ch07_181_bin_moveit_scene_contract import exact_bin_collision_from_world
S='''<sdf><world name="book_camera"><model name="g04_bin_support">
<static>true</static><pose>0.55 0.25 1.63 0 0 0</pose>
<link name="bin_support"><collision name="bin_collision">
<geometry><box><size>0.30 0.30 0.20</size></box></geometry>
</collision></link></model></world></sdf>'''
class TestCycle12Fixture(unittest.TestCase):
 def mk(self,s=S):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
  p=Path(d.name)/'w.sdf';p.write_text(s)
  return p,Path(d.name)/'a.json'
 def test_physically_present_bin_same_size_and_moveit_full_pose(self):
  p,a=self.mk();x=rotate_bin(p,a)
  self.assertEqual(x["only_change"],"real_bin_model_yaw_0_to_0.35_rad")
  self.assertEqual(x["bin_dimensions_m"],[.30,.30,.20])
  with self.assertRaises(ValueError):exact_bin_collision_from_world(p)
  spec=exact_bin_collision_from_world(p,allow_cycle12_yaw=True)
  self.assertEqual(spec["bin_yaw_rad"],.35)
  self.assertEqual(spec["box_m"],[.30,.30,.20])
  self.assertGreater(spec["quaternion_xyzw"][2],0)
  with self.assertRaises(ValueError):rotate_bin(p,a)
 def test_changed_obstacle_size_or_position_fails(self):
  for x in (S.replace("0.30 0.30 0.20","0.20 0.20 0.20"),
            S.replace("0.55 0.25","0.50 0.25")):
   p,a=self.mk(x)
   with self.assertRaises(ValueError):rotate_bin(p,a)
if __name__=="__main__":unittest.main()
