"""ROS-free static SDF contract tests."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description/worlds/my_world.sdf"
class WorldTests(unittest.TestCase):
    def test_world_and_physics(self):
        root=ET.parse(P).getroot()
        self.assertEqual(root.attrib["version"],"1.8")
        w=root.find("world")
        self.assertEqual(w.attrib["name"],"my_first_world")
        self.assertEqual(w.find("gravity").text.strip(),"0 0 -9.80665")
        self.assertEqual(w.find("physics/max_step_size").text.strip(),"0.001")
        plugins={p.attrib["name"] for p in w.findall("plugin")}
        self.assertTrue({"gz::sim::systems::Physics","gz::sim::systems::UserCommands","gz::sim::systems::SceneBroadcaster"} <= plugins)
    def test_ground_is_static(self):
        root=ET.parse(P).getroot()
        model=next(x for x in root.findall("world/model") if x.attrib["name"]=="ground_plane")
        self.assertEqual(model.find("static").text.strip(),"true")
if __name__=="__main__": unittest.main()
