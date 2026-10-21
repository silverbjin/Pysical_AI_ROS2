"""ROS-free checks for YAML bridge topic contracts."""
import ast
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description"
class BridgeTests(unittest.TestCase):
    def test_active_mapping(self):
        source=(P/"config/ros_gz_bridge.yaml").read_text()
        active="\n".join(l for l in source.splitlines() if not l.lstrip().startswith("#"))
        self.assertEqual(active.count("- ros_topic_name:"),4)
        self.assertNotIn("cmd_vel",active)
        self.assertNotIn('ros_topic_name: "/tf"',active)
        for name in ("/clock","/joint_states","/joint1/cmd_pos","/joint2/cmd_pos"):
            self.assertIn('ros_topic_name: "'+name+'"',active)
        self.assertEqual(active.count("direction: ROS_TO_GZ"),2)
        self.assertEqual(active.count("direction: GZ_TO_ROS"),2)
    def test_python_launch_syntax(self):
        source=(P/"launch/bridge.launch.py").read_text()
        ast.parse(source)
        self.assertIn("'config_file': bridge_config_file",source)
if __name__=="__main__": unittest.main()
