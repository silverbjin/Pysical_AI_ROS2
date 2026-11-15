"""Issue #181: only high transport is slowed; fail closed on invalid stage."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ch07_181_high_carry_motion_contract import velocity_scaling_for_arm_goal, BASE_VELOCITY_SCALING, HIGH_VELOCITY_SCALING, ARM_ACCELERATION_SCALING

class HighCarryVelocityTDD(unittest.TestCase):
    def test_only_high_transport_half_speed(self):
        self.assertEqual(BASE_VELOCITY_SCALING, .17)
        self.assertEqual(HIGH_VELOCITY_SCALING, .085)
        self.assertAlmostEqual(velocity_scaling_for_arm_goal('transfer_high_above_bin')*2, BASE_VELOCITY_SCALING)
        for stage in ('lift', 'lower_into_bin','pregrasp','x_approach_clearance_stage','approach'):
            self.assertEqual(velocity_scaling_for_arm_goal(stage), BASE_VELOCITY_SCALING)
    def test_acceleration_and_physics_not_modified_by_selector(self):
        self.assertEqual(ARM_ACCELERATION_SCALING, .17)
        self.assertEqual(velocity_scaling_for_arm_goal('transfer_high_above_bin'), .085)
    def test_invalid_goal_labels_fail_closed(self):
        for label in ('', None, 12):
            with self.assertRaises(ValueError):
                velocity_scaling_for_arm_goal(label)

if __name__ == '__main__': unittest.main()
