"""4.5절 Xacro·RSP·JointState 연결 정적 검사."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestStatePublisherLaunch(unittest.TestCase):
    def test_launch_uses_actual_ch03_model(self):
        source = (ROOT / "launch/display_ch04.launch.py").read_text()
        ast.parse(source)
        self.assertIn('"two_dof_arm.urdf.xacro"', source)
        self.assertNotIn('os.path.join(model_dir, "urdf", "robot.urdf.xacro")', source)
        self.assertIn('ParameterValue(Command(["xacro ", xacro_file]), value_type=str)', source)

    def test_rSP_jSP_own_responsibilities(self):
        source = (ROOT / "launch/display_ch04.launch.py").read_text()
        self.assertIn('package="robot_state_publisher"', source)
        self.assertIn('package="joint_state_publisher_gui"', source)
        self.assertNotIn("ros_gz_bridge", source)

    def test_rviz_uses_transient_local_description(self):
        config = (ROOT / "rviz/display_ch04.rviz").read_text()
        self.assertIn("Fixed Frame: base_link", config)
        self.assertIn("Durability Policy: Transient Local", config)


if __name__ == "__main__":
    unittest.main()
