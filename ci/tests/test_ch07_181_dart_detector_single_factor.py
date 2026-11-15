#!/usr/bin/env python3
import pathlib,sys,tempfile,unittest,xml.etree.ElementTree as ET
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_dart_detector_single_factor import (
 isolate_one_detector_factor,CANDIDATE_DETECTOR)
ORIGINAL="""<sdf version="1.10"><world name="book_camera">
 <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
 <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size></physics>
 <gravity>0 0 -9.8</gravity>
 <model name="g04_grasp_cylinder"><static>false</static>
  <link name="cylinder_link"><inertial><mass>0.05</mass></inertial>
   <collision name="cylinder_collision"><surface><friction><ode>
   <mu>1</mu></ode></friction></surface></collision></link></model>
 </world></sdf>"""
class DartDetectorSingleFactorTDD(unittest.TestCase):
 def test_only_collision_detector_changes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"world.sdf";a=pathlib.Path(d)/"proof.json"
   p.write_text(ORIGINAL)
   orig=ET.parse(p).getroot()
   receipt=isolate_one_detector_factor(p,a)
   new=ET.parse(p).getroot()
   self.assertEqual(receipt["candidate_detector"],"fcl")
   self.assertEqual(new.findtext("./world/physics/dart/collision_detector"),"fcl")
   self.assertEqual(new.findtext("./world/physics/max_step_size"),"0.001")
   self.assertEqual(new.findtext("./world/gravity"),"0 0 -9.8")
   self.assertEqual(new.findtext("./world/model/static"),"false")
   self.assertEqual(new.findtext("./world/model/link/inertial/mass"),"0.05")
   self.assertEqual(new.findtext(".//friction/ode/mu"),"1")
   self.assertFalse(receipt["force_attach_or_teleport"])
 def test_nonoriginal_gravity_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf";p.write_text(ORIGINAL.replace("-9.8","0"))
   with self.assertRaises(ValueError):isolate_one_detector_factor(p,pathlib.Path(d)/"r")
 def test_existing_dart_configuration_cannot_be_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf";p.write_text(ORIGINAL.replace(
     "</physics>","<dart><collision_detector>bullet</collision_detector></dart></physics>"))
   with self.assertRaises(ValueError):isolate_one_detector_factor(p,pathlib.Path(d)/"r")
 def test_wrong_mass_cannot_mislabel_as_same_physics(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/"w.sdf";p.write_text(ORIGINAL.replace("0.05","0.5"))
   with self.assertRaises(ValueError):isolate_one_detector_factor(p,pathlib.Path(d)/"r")
if __name__=="__main__":unittest.main()
