"""ROS-free geometric approximations for Chapter 3.5."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description/urdf/two_dof_arm.urdf"
class GeometryTests(unittest.TestCase):
    def test_collision_matches_box_extent(self):
        root=ET.parse(P).getroot()
        links={x.attrib["name"]:x for x in root.findall("link")}
        for name in ("link1","link2"):
            link=links[name]
            visual=link.find("visual/geometry/box")
            collision=link.find("collision/geometry/box")
            self.assertIsNotNone(visual)
            self.assertIsNotNone(collision)
            self.assertEqual(visual.attrib["size"],collision.attrib["size"])
    def test_uniform_box_approximation(self):
        root=ET.parse(P).getroot()
        for link in root.findall("link"):
            if link.attrib["name"] not in ("link1","link2"):continue
            inertia=link.find("inertial/inertia").attrib
            self.assertAlmostEqual(float(inertia["ixx"]),(0.05**2 + 0.5**2)/12,places=8)
            self.assertAlmostEqual(float(inertia["izz"]),(0.05**2 + 0.05**2)/12,places=8)
if __name__=="__main__": unittest.main()
