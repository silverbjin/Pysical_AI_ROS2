"""ROS-free consistency tests for the two Chapter 3 simulation launches."""
import ast
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description/launch"
class LaunchTests(unittest.TestCase):
    def test_no_duplicate_systems(self):
        sync=(P/"sim_sync.launch.py").read_text()
        ast.parse(sync)
        self.assertIn("'spawn_robot.launch.py'",sync)
        self.assertNotIn("empty.sdf",sync)
        self.assertNotIn("executable='parameter_bridge'",sync)
        self.assertNotIn("executable='robot_state_publisher'",sync)
    def test_canonical_world_and_bridge(self):
        spawn=(P/"spawn_robot.launch.py").read_text()
        ast.parse(spawn)
        self.assertIn("'my_world.sdf'",spawn)
        self.assertIn("'ros_gz_bridge.yaml'",spawn)
        self.assertIn("'my_robot'",spawn)
if __name__=="__main__": unittest.main()
