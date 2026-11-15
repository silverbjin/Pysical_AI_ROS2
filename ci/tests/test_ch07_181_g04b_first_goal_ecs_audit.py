#!/usr/bin/env python3
import sys,unittest,tempfile,csv,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_g04b_first_goal_ecs_audit import audit,main

def first():
    return {"name":"lower_stop_release_both_fingers_2mm",
            "actual_m":{"joint_finger1":0.,"joint_finger2":.002},
            "first_goal_causal_receipt":{
             "goal_start_sim_s":36.,"goal_end_sim_s":41.,
             "finger_results":{
               "joint_finger1":{"first_known_boundary":"HARDWARE_COMMAND_PRESENT_NATIVE_GAZEBO_UNCLASSIFIED",
                                "hardware_command_peak_m":.002,"reference_peak_m":.002,
                                "actual_final_m":0.},
               "joint_finger2":{"first_known_boundary":"PHYSICAL_JOINT_REACHED_SCOPED",
                                "hardware_command_peak_m":.002,"reference_peak_m":.002,
                                "actual_final_m":.002}}}}

def rec(name,t,phase,cmd,pos):
    return {"joint_name":name,"sim_time_s":str(t),"phase":phase,
            "velocity_cmd_mps":str(cmd),"position_m":str(pos)}
class TestFirstFingerEcsAudit(unittest.TestCase):
    def test_nonzero_cmd_but_native_joint_frozen_is_not_success(self):
        data=[rec("joint_finger1",38,"pre",.02,0.),
              rec("joint_finger1",39,"post",0.,0.),
              rec("joint_finger2",38,"pre",.02,0.),
              rec("joint_finger2",39,"post",0.,.002)]
        r=audit(first(),iter(data))
        self.assertEqual(r["joint_ecs"]["joint_finger1"]["first_boundary"],
                         "ECS_NONZERO_CMD_BUT_NATIVE_JOINT_FROZEN")
        self.assertEqual(r["joint_ecs"]["joint_finger2"]["first_boundary"],
                         "NATIVE_JOINT_MOVED_SCOPED")
        self.assertEqual(r["G04B"],"BLOCKED")
    def test_missing_samples_are_unknown_not_zero_cmd(self):
        r=audit(first(),[])
        self.assertEqual(r["joint_ecs"]["joint_finger1"]["first_boundary"],
                         "NATIVE_ECS_UNOBSERVED")
        self.assertEqual(r["verdict"],
                         "INCOMPLETE_NATIVE_ECS_EVIDENCE_G04B_STILL_BLOCKED")
    def test_post_abort_controller_reference_cannot_prove_goal_sent(self):
        goal=first()
        goal["first_goal_causal_receipt"]["finger_results"]["joint_finger1"][
             "first_known_boundary"]="JTC_REFERENCE_UNOBSERVED"
        r=audit(goal,[rec("joint_finger1",38,"pre",.02,0.),
                      rec("joint_finger2",38,"pre",.02,0.)])
        self.assertEqual(r["joint_ecs"]["joint_finger1"]["first_boundary"],
                         "JTC_REFERENCE_UNOBSERVED_DO_NOT_INFER_HARDWARE")
    def test_no_receipt_keeps_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);out=main(p/"missing.json",p/"ecs.csv",p/"result.json")
            self.assertEqual(out["G04B"],"BLOCKED")
            self.assertEqual(out["verdict"],"FIRST_GOAL_OR_NATIVE_ECS_MISSING")
if __name__=="__main__":unittest.main()
