#!/usr/bin/env python3
import csv,pathlib,sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_ecs_trace_audit import summarize,classify,generate
def sample(t,phase,cmd,actual=0):
 return {"sim_time_s":str(t),"phase":phase,"joint_entity":"7",
         "velocity_cmd_present":"1","velocity_cmd_size":"1",
         "velocity_cmd_mps":str(cmd),"position_present":"1",
         "position_m":str(actual),"velocity_present":"1",
         "velocity_mps":"0","force_cmd_present":"0","force_cmd_n":"nan"}
class EcsAudit(unittest.TestCase):
 def test_ecs_nonzero_velocity_plus_frozen_native_is_physics_boundary(self):
  summary=summarize([sample(10,"pre",0.1),sample(10.01,"post",0)],9,12)
  self.assertEqual(classify(summary,.011,0.),
                  "ECS_NONZERO_VELOCITY_CMD_WHILE_NATIVE_JOINT_FROZEN")
 def test_command_zero_in_samples_cannot_prove_plugin_never_wrote(self):
  summary=summarize([sample(10,"pre",0),sample(10.01,"post",0)],9,12)
  self.assertEqual(classify(summary,.011,0.),
                  "ECS_NONZERO_CMD_NOT_OBSERVED_AT_SAMPLED_PHASES")
 def test_missing_goal_window_is_not_green(self):
  summary=summarize([sample(1,"pre",.1)],9,12)
  self.assertEqual(classify(summary,.011,0.),
                  "ECS_UNOBSERVED_CAUSE_UNDETERMINED")
 def test_missing_csv_never_passes(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   out=generate(root/"none.csv",root/"none.json",root/"out.json")
   self.assertEqual(out["verdict"],"WITNESS_RECEIPT_MISSING")
   self.assertEqual(out["G04B"],"BLOCKED")
 def test_partial_nonzero_is_proof_of_ecs_component(self):
  summary=summarize([sample(10,"pre",.045),
                     sample(10.02,"post",0)],9,12)
  self.assertEqual(summary["by_phase"]["pre"]["velocity_cmd_nonzero_samples"],1)
 def test_g04b_never_marked_pass_when_ecs_speed_seen(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);csvp=root/"ecs.csv";out=root/"out.json";w=root/"witness.json"
   with csvp.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(sample(10,"pre",.1)))
    writer.writeheader();writer.writerow(sample(10,"pre",.1))
   w.write_text(json.dumps({"per_goal_results":[{
    "label":"finger2","before_stamp":9.0,"after_stamp":11.0,
    "hardware_command_peak_candidates":{"command_interface.joint_finger2/position":.011},
    "measured_fingers":{"joint_finger2":0.0}}]}))
   result=generate(csvp,w,out)
   self.assertEqual(result["G04B"],"BLOCKED")
   self.assertEqual(result["verdict"],"ECS_NONZERO_VELOCITY_CMD_WHILE_NATIVE_JOINT_FROZEN")
if __name__=="__main__":unittest.main()
