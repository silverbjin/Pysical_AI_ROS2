"""ROS-free structural tests for Chapter 3.2."""
import ast
import math
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
PKG = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_description"
class TwoDofStaticTests(unittest.TestCase):
    def test_chain_and_inertia(self):
        root = ET.parse(PKG / "urdf/two_dof_arm.urdf").getroot()
        links = {e.attrib["name"]: e for e in root.findall("link")}
        self.assertEqual(set(links), {"base_link","link1","link2","end_effector_link"})
        self.assertEqual(len(root.findall("joint")), 3)
        self.assertAlmostEqual(float(links["base_link"].find("inertial/inertia").attrib["ixx"]), 10*(3*.1**2+.1**2)/12, places=8)
        self.assertAlmostEqual(float(links["end_effector_link"].find("inertial/inertia").attrib["ixx"]), .4*.01*.02**2, places=10)
        self.assertEqual(links["link1"].find("visual/origin").attrib["rpy"], "0 0 0")
    def test_launch_syntax_and_dependency(self):
        source = (PKG / "launch/display.launch.py").read_text()
        ast.parse(source)
        self.assertIn("LaunchConfiguration('model')", source)
        self.assertIn("default_value='two_dof_arm.urdf'", source)
        dep = ET.parse(PKG / "package.xml").getroot()
        self.assertIn("ros_gz_sim", [x.text for x in dep.findall("exec_depend")])
if __name__ == "__main__": unittest.main()
