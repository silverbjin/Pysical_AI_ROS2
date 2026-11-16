"""Fail-closed MoveIt-vs-Gazebo exact bin geometry contract."""
import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_bin_moveit_scene_contract import exact_bin_collision_from_world
S='''<sdf version="1.10"><world name="book_camera">
<model name="g04_bin_support"><static>true</static><pose>0.55 0.25 1.63 0 0 0</pose>
<link name="bin_support"><collision name="bin_collision">
<geometry><box><size>0.30 0.30 0.20</size></box></geometry></collision></link></model>
</world></sdf>'''
class Contract(unittest.TestCase):
 def fixture(self,text):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
  p=Path(t.name)/"w.sdf";p.write_text(text);return p
 def test_exact_object_read_only(self):
  p=self.fixture(S);before=p.read_bytes()
  x=exact_bin_collision_from_world(p)
  self.assertEqual(x["frame_id"],"base_link")
  self.assertEqual(x["center_m"],[.55,.25,1.63])
  self.assertEqual(x["box_m"],[.30,.30,.20])
  self.assertEqual(p.read_bytes(),before)
 def test_changed_collision_or_pose_rejected(self):
  for s in [S.replace("0.55 0.25","0.56 0.25"),
            S.replace("0.30 0.30 0.20","0.30 0.25 0.20"),
            S.replace("<static>true","<static>false"),
            S.replace("<geometry><box>","<pose>0 0 .1 0 0 0</pose><geometry><box>")]:
   with self.assertRaises(ValueError):
    exact_bin_collision_from_world(self.fixture(s))
if __name__=="__main__":unittest.main()
