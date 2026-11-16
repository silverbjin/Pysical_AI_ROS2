#!/usr/bin/env python3
"""Cycle07 fail-closed sensor test: observation only, same physical world."""
import sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_bin_contacts_readonly import add_bin_contact_sensor,SENSOR_NAME
XML='''<sdf version="1.10"><world name="book_camera">
<physics><max_step_size>0.001</max_step_size><dart><solver><solver_type>pgs</solver_type></solver></dart></physics>
<gravity>0 0 -9.8</gravity>
<plugin filename="gz-sim-contact-system" name="gz::sim::systems::Contact"/>
<model name="g04_bin_support"><static>true</static><pose>.55 .25 1.63 0 0 0</pose>
<link name="bin_support"><collision name="bin_collision">
<geometry><box><size>0.30 0.30 0.20</size></box></geometry>
</collision></link></model>
<model name="g04_grasp_cylinder"><static>false</static>
<link name="cylinder_link"><inertial><mass>.05</mass></inertial></link></model>
</world></sdf>'''
class BinContactReadOnly(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.world=Path(self.tmp.name)/"world.sdf"
  self.rec=Path(self.tmp.name)/"receipt.json"
  self.world.write_text(XML)
 def test_only_sensor_added_original_geometry_and_solver_identical(self):
  old=ET.fromstring(self.world.read_text())
  r=add_bin_contact_sensor(self.world,self.rec)
  self.assertEqual(r["changed_only"],"g04_bin_support/bin_support/sensor")
  new=ET.parse(self.world).getroot()
  sensor=new.find(".//model[@name='g04_bin_support']/link/sensor")
  self.assertEqual(sensor.get("name"),SENSOR_NAME)
  self.assertEqual(sensor.findtext("contact/collision"),"bin_collision")
  parent=new.find(".//model[@name='g04_bin_support']/link")
  parent.remove(sensor)
  self.assertEqual(ET.tostring(old),ET.tostring(new))
  self.assertEqual(new.findtext("./world/physics/dart/solver/solver_type"),"pgs")
  self.assertEqual(new.findtext(".//collision/geometry/box/size"),"0.30 0.30 0.20")
 def test_missing_collision_plugin_or_changed_shape_refused(self):
  for bad in (XML.replace("0.30 0.30 0.20","0.25 0.25 0.20"),
              XML.replace("gz-sim-contact-system","gz-sim-other-system"),
              XML.replace("<static>true</static>","<static>false</static>")):
   self.world.write_text(bad)
   with self.assertRaises(ValueError):
    add_bin_contact_sensor(self.world,self.rec)
 def test_duplicate_contact_sensor_refused(self):
  add_bin_contact_sensor(self.world,self.rec)
  with self.assertRaises(ValueError):
   add_bin_contact_sensor(self.world,self.rec)
if __name__=="__main__":unittest.main()
