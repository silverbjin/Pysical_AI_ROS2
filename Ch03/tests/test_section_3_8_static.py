"""Source-only tests for Gazebo system plugin and joint settings."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description/urdf/two_dof_arm.urdf.xacro"
class ControlContractTests(unittest.TestCase):
    def test_joint_limits_and_damping(self):
        root=ET.parse(P).getroot()
        joints={j.attrib["name"]:j for j in root.findall("joint")}
        for name in ("joint1","joint2"):
            self.assertEqual(joints[name].find("dynamics").attrib["damping"],"0.1")
            self.assertEqual(joints[name].find("limit").attrib["effort"],"100")
    def test_plugins_and_command_bounds(self):
        root=ET.parse(P).getroot()
        plugins=root.findall("gazebo/plugin")
        states=[p for p in plugins if p.attrib.get("name","").endswith("JointStatePublisher")]
        ctrls=[p for p in plugins if p.attrib.get("name","").endswith("JointPositionController")]
        self.assertEqual(len(states),1)
        self.assertEqual(states[0].find("update_rate").text.strip(),"50")
        self.assertEqual(len(ctrls),2)
        self.assertEqual({p.find("joint_name").text.strip() for p in ctrls},{"joint1","joint2"})
        j1=next(p for p in ctrls if p.find("joint_name").text.strip()=="joint1")
        self.assertEqual(j1.find("cmd_max").text.strip(),"100")
        self.assertEqual(j1.find("cmd_min").text.strip(),"-100")
if __name__=="__main__": unittest.main()
