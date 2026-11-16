"""Fail-closed first-finger causal classifier tests; no ROS/Gazebo import."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_g04b_first_goal_causal_contract import first_goal_evidence

def row(t,ref,feedback):
    return {"stamp":t,"names":["joint_finger1","joint_finger2"],
            "reference":ref,"feedback":feedback,
            "error":[ref[0]-feedback[0],ref[1]-feedback[1]]}

class TestFingerFirstGoalCausalEvidence(unittest.TestCase):
    def test_original_post_abort_snapshot_not_misclassified_as_missing_goal(self):
        # Original #202 last ctrl_state after ABORTED resets ref to actual.
        post=row(41.038,[6.3498108344e-9,.002],[6.3683234448e-9,.002])
        receipt=first_goal_evidence([post],[],
               {"joint_finger1":6.3683234448e-9,"joint_finger2":.002},
               36.99,41.04)
        self.assertEqual(receipt["finger_results"]["joint_finger1"]
                         ["first_known_boundary"],"JTC_REFERENCE_UNOBSERVED")
        self.assertEqual(receipt["hardware_command_samples_in_goal"],0)

    def test_reference_reached_but_command_unknown_is_not_physics_claim(self):
        s=[row(37.0,[.002,.002],[0,.002])]
        receipt=first_goal_evidence(s,[],
                {"joint_finger1":0.,"joint_finger2":.002},36.99,38.)
        self.assertEqual(receipt["finger_results"]["joint_finger1"]
                         ["first_known_boundary"],"JTC_GOAL_REACHED_HARDWARE_UNOBSERVED")
        self.assertEqual(receipt["finger_results"]["joint_finger2"]
                         ["first_known_boundary"],"PHYSICAL_JOINT_REACHED_SCOPED")

    def test_actual_hardware_command_must_be_explicitly_named(self):
        samples=[{"sim_observed_s":37.5,"values":{
          "state_interface.joint_finger1/position":.002,
          "command_interface.joint_finger1/position":.002}}]
        r=first_goal_evidence([row(37.5,[.002,.002],[0,.002])],samples,
                {"joint_finger1":0.,"joint_finger2":.002},37.,38.)
        self.assertEqual(r["finger_results"]["joint_finger1"]
                         ["first_known_boundary"],
                         "HARDWARE_COMMAND_PRESENT_NATIVE_GAZEBO_UNCLASSIFIED")
        self.assertEqual(r["finger_results"]["joint_finger1"]
                         ["hardware_command_peak_m"],.002)

    def test_missing_hardware_command_not_falsely_counted(self):
        s=[{"sim_observed_s":37.5,"values":{
            "state_interface.joint_finger1/position":.002}}]
        r=first_goal_evidence([row(37.5,[.002,.002],[0,.002])],s,
                {"joint_finger1":0.,"joint_finger2":.002},37.,38.)
        self.assertIsNone(r["finger_results"]["joint_finger1"]
                          ["hardware_command_peak_m"])

    def test_invalid_or_mismatched_timing_is_fail_closed(self):
        with self.assertRaises(ValueError):
            first_goal_evidence([],[],{"joint_finger1":0.},1.,2.)
        with self.assertRaises(ValueError):
            first_goal_evidence([],[],{"joint_finger1":0.,
                                      "joint_finger2":float("nan")},1.,2.)
        with self.assertRaises(ValueError):
            first_goal_evidence([],[],{"joint_finger1":0.,"joint_finger2":0.},
                                2.,1.)
if __name__=="__main__":unittest.main()
