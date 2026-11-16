#!/usr/bin/env python3
"""L0 negative source contract: joint2 trace must be passive; never fake physics."""
import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ArmJoint2ReadOnlyContract(unittest.TestCase):
    def test_native_gazebo_trace_includes_arm_joint2_without_mutating_ecm(self):
        s=(ROOT/"ch07_181_rod_trace/finger_ecs_trace.cc").read_text()
        self.assertIn('{"joint_finger1","joint_finger2","joint2","joint3"}',s)
        for forbidden in ("CreateComponent(", "SetComponentData(", "SetVelocity(", "SetForce("):
            self.assertNotIn(forbidden,s)
        self.assertIn("components::JointVelocityCmd",s)
        self.assertIn("components::JointPosition",s)
    def test_full_fjt_failure_preserves_joint2_controller_hw_and_ecs_interval(self):
        s=(ROOT/"ch07_77_g04b_actual_physics_witness.py").read_text()
        for marker in ("on_arm_joint2_controller_state",
                       '"/arm_group_controller/controller_state"',
                       '"command_interface.joint2/position"',
                       '"last_arm_settle_even_on_failure"',
                       '"jtc_reference_feedback_error"',
                       '"hardware_command_position"',
                       'gazebo_finger_ecs_pre_post_command.csv',
                       '"READ_ONLY_NOT_PHYSICAL_PASS"'):
            self.assertIn(marker,s)
        self.assertIn('raise RuntimeError("G04B_181_ARM_SETTLE_FAILED_"+str(row))',s)
        self.assertIn('if verdict!="ARM_SETTLE_SCOPED_PASS":',s)
    def test_no_acceptance_or_tolerance_relaxation(self):
        w=(ROOT/"ch07_77_g04b_verify_contacts.py").read_text()
        for criterion in ("real_both_fingers_positive_force",
                          "real_dynamic_world_lift_at_least_0_05m",
                          "1_3s_hold_pose_drift_le_0_025m",
                          "placement_xy_error_le_0_09m"):
            self.assertIn(criterion,w)
if __name__=="__main__": unittest.main()
