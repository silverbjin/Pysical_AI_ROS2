"""Standalone standard-library static tests for Chapter 3.1."""
import math
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_description/urdf/simple_arm.urdf"
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ET.parse(P).getroot()
    def test_unique_model_chain(self):
        self.assertEqual(self.root.attrib["name"], "simple_bot")
        self.assertEqual([x.attrib["name"] for x in self.root.findall("link")], ["base_link", "link1"])
        joint = self.root.find("joint")
        self.assertEqual(joint.attrib["type"], "revolute")
        self.assertEqual(joint.find("parent").attrib["link"], "base_link")
        self.assertEqual(joint.find("child").attrib["link"], "link1")
        self.assertEqual(joint.find("axis").attrib["xyz"], "0 0 1")
    def test_center_of_mass_and_inertia(self):
        for link, height, expected_ixx in (("base_link", 0.025, 5*(3*.1**2 + .05**2)/12), ("link1", .15, (.05**2 + .3**2)/12)):
            item = next(x for x in self.root.findall("link") if x.attrib["name"] == link)
            self.assertAlmostEqual(float(item.find("inertial/origin").attrib["xyz"].split()[2]), height)
            self.assertAlmostEqual(float(item.find("inertial/inertia").attrib["ixx"]), expected_ixx, places=8)
if __name__ == "__main__": unittest.main()
