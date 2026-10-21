"""4.6절 Gazebo bridge 및 시뮬레이션 시계 정적 계약."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestSimulationSyncContract(unittest.TestCase):
    def test_source_and_bridge_match(self):
        source = (ROOT / "launch/sim_sync_ch04.launch.py").read_text()
        ast.parse(source)
        self.assertIn('"two_dof_arm.urdf.xacro"', source)
        self.assertIn('"gz_args": "-r empty.sdf"', source)
        self.assertIn('"/world/empty/model/my_robot/joint_state"', source)
        self.assertIn('"@sensor_msgs/msg/JointState[gz.msgs.Model"', source)
        self.assertIn('("/world/empty/model/my_robot/joint_state", "/joint_states")', source)

    def test_clock_and_rSP(self):
        source = (ROOT / "launch/sim_sync_ch04.launch.py").read_text()
        self.assertIn("/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock", source)
        self.assertGreaterEqual(source.count('"use_sim_time": use_sim_time'), 2)
        self.assertNotIn("joint_state_publisher_gui", source)

    def test_rviz_fixed_frame(self):
        rviz = (ROOT / "rviz/sim_sync_ch04.rviz").read_text()
        self.assertIn("Fixed Frame: base_link", rviz)
        self.assertIn("Durability Policy: Transient Local", rviz)


if __name__ == "__main__":
    unittest.main()
