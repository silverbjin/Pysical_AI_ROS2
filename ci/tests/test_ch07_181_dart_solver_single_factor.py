#!/usr/bin/env python3
import pathlib,tempfile,sys,unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_dart_solver_single_factor import apply_one_solver_factor
SOURCE="""<sdf version="1.10"><world name="book_camera">
<physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size></physics>
<gravity>0 0 -9.8</gravity><model name="g04_grasp_cylinder"><static>false</static>
<link name="cylinder_link"><inertial><mass>0.05</mass></inertial>
<collision name="cylinder_collision"><geometry><cylinder><radius>0.012</radius>
<length>0.08</length></cylinder></geometry></collision></link></model></world></sdf>"""
class DartPGSOnlyTDD(unittest.TestCase):
 def test_only_dantzig_to_pgs_and_no_collision_geometry_or_model_change(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf";a=pathlib.Path(d)/"r.json";p.write_text(SOURCE)
   report=apply_one_solver_factor(p,a);root=ET.parse(p).getroot()
   self.assertEqual(root.findtext("./world/physics/dart/solver/solver_type"),"pgs")
   self.assertIsNone(root.find("./world/physics/dart/collision_detector"))
   self.assertEqual(root.findtext("./world/physics/max_step_size"),"0.001")
   self.assertEqual(root.findtext("./world/model/static"),"false")
   self.assertEqual(root.findtext("./world/model/link/inertial/mass"),"0.05")
   self.assertFalse(report["forced_attach"]);self.assertFalse(report["teleport"])
 def test_cannot_stack_fcl_with_solver_factor(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf";p.write_text(SOURCE.replace(
   "</physics>","<dart><collision_detector>fcl</collision_detector></dart></physics>"))
   with self.assertRaises(ValueError):apply_one_solver_factor(p,pathlib.Path(d)/"r.json")
 def test_world_mass_and_gravity_immutability_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf"
   p.write_text(SOURCE.replace("0.05","0.50"))
   with self.assertRaises(ValueError):apply_one_solver_factor(p,pathlib.Path(d)/"r.json")
if __name__=="__main__":unittest.main()
