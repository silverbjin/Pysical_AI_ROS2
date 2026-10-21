"""Xacro source tests; xacro expansion requires ROS environment."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "ros2_ws/src/my_robot_description/urdf/two_dof_arm.urdf.xacro"
NS={"x":"http://www.ros.org/wiki/xacro"}
class XacroTests(unittest.TestCase):
    def test_macros(self):
        root=ET.parse(P).getroot()
        macros={x.attrib["name"]:x for x in root.findall("x:macro",NS)}
        self.assertTrue({"box_inertia","cylinder_inertia","arm_link_macro"} <= set(macros))
        inert=macros["box_inertia"].find("inertial")
        self.assertEqual(inert.find("origin").attrib["xyz"], "0 0 ${h/2}")
        terms=inert.find("inertia").attrib
        self.assertIn("h*h + d*d",terms["ixx"])
        self.assertIn("w*w + h*h",terms["iyy"])
        self.assertIn("w*w + d*d",terms["izz"])
    def test_ee(self):
        root=ET.parse(P).getroot()
        self.assertIn("joint_ee",[j.attrib["name"] for j in root.findall("joint")])
        self.assertIn("end_effector_link",[l.attrib["name"] for l in root.findall("link")])
if __name__=="__main__": unittest.main()
