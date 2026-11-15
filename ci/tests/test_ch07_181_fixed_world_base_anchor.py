"""Six TDD cases: Gazebo world base fixed, original articulated robot untouched."""
import sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_fixed_world_base_anchor import anchored_world_base_model,ANCHOR_NAME
SRC='<sdf version="1.10"><model name="my_robot"><link name="base_link"/>' + ''.join(f'<link name="link{i}"/>' for i in range(1,8)) + '<plugin name="original_ros2_control" filename="gz_ros2_control-system"/>' + ''.join(f'<joint name="joint{i}" type="revolute"><parent>base_link</parent><child>link{i}</child></joint>' for i in range(1,8)) + '</model></sdf>'
class TestG04BPhysicalWorldBaseFix(unittest.TestCase):
 def test_one_world_base_joint(self):
  out,r=anchored_world_base_model(SRC)
  a=ET.fromstring(out)
  j=a.find(".//joint[@name='"+ANCHOR_NAME+"']")
  self.assertIsNotNone(j)
  self.assertEqual((j.get('type'),j.findtext('parent'),j.findtext('child')),('fixed','world','base_link'))
  self.assertEqual(len(a.findall('.//joint')),8)
  self.assertEqual(r['G04B'],'BLOCKED_PENDING_REAL_GAZEBO')
 def test_original_robot_other_elements_untouched(self):
  out,_=anchored_world_base_model(SRC)
  a=ET.fromstring(out)
  a.find('./model').remove(a.find(".//joint[@name='"+ANCHOR_NAME+"']"))
  self.assertEqual(ET.tostring(a),ET.tostring(ET.fromstring(SRC)))
 def test_no_rod_teleport_or_attach(self):
  out,r=anchored_world_base_model(SRC)
  self.assertNotIn('g04_grasp_cylinder',out)
  self.assertFalse(r['rod_and_world_physics_changed'])
  self.assertFalse(r['object_attach_or_teleport'])
 def test_missing_base_fails_closed(self):
  with self.assertRaises(ValueError):
   anchored_world_base_model(SRC.replace('name="base_link"','name="other_base"',1))
 def test_duplicate_anchor_fails_closed(self):
  out,_=anchored_world_base_model(SRC)
  with self.assertRaises(ValueError):anchored_world_base_model(out)
 def test_static_or_changed_joint_count_fails_closed(self):
  with self.assertRaises(ValueError):
   anchored_world_base_model(SRC.replace('<model name="my_robot">','<model name="my_robot"><static>true</static>'))
  with self.assertRaises(ValueError):
   anchored_world_base_model(SRC.replace('</model>','<joint name="extra" type="fixed"><parent>base_link</parent><child>link1</child></joint></model>'))
if __name__=='__main__':unittest.main()
