#!/usr/bin/env python3
import pathlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_native_recent_contact import (
 recent_native_finger_rod_contact,require_bilateral_pre_release_contact,
 require_bilateral_same_ecs_frame_force)
def block(finger,t,force=.7):
 sec=int(t);ns=int((t-sec)*1e9)
 return (f"header {{\n  stamp {{\n  sec: {sec}\n  nsec: {ns}\n }}\n}}\n"
 f"contact {{\n header {{ stamp {{ sec: {sec} nsec: {ns} }} }}\n"
 f' collision1 {{ name: "my_robot::{finger}::{finger}_collision" }}\n'
 ' collision2 { name: "g04_grasp_cylinder::cylinder_link::cylinder_collision" }\n'
 f" wrench {{ body_1_wrench {{ force {{ x: {force} y: 0 z: 0 }} }} }}\n}}\n")
class RecentNativeContactTDD(unittest.TestCase):
 def test_bilateral_fresh_positive_force_passes(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   for name in ('finger1','finger2'):
    (p/f"diag_{name}_contacts.log").write_text(
      "".join("\n"+block(name,66.6+i*.05) for i in range(5)))
   r=require_bilateral_pre_release_contact(p,67.0)
   self.assertTrue(r["both_native_fresh_positive_force"])
 def test_stale_or_absent_or_wrong_pair_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   (p/"diag_finger1_contacts.log").write_text(
     "".join("\n"+block("finger1",65.0+i*.01) for i in range(4)))
   r=require_bilateral_pre_release_contact(p,67.0)
   self.assertFalse(r["both_native_fresh_positive_force"])
 def test_contact_force_zero_does_not_pass(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"diag_finger1_contacts.log"
   p.write_text("".join("\n"+block("finger1",66.7+i*.01,0.0)
                        for i in range(4)))
   self.assertFalse(recent_native_finger_rod_contact(p,'finger1',67.0)[
     "native_positive_force_fresh"])
 def test_invalid_time_refused(self):
  with self.assertRaises(ValueError):
   recent_native_finger_rod_contact('/tmp/nonexistent','finger3',67.0)

class SameEcsForceTDD(unittest.TestCase):
 def _line(self,t,c1=1,c2=1,f1=.7,f2=.58):
  return f"{t},1,1,{c1},{f1},1,1,{c2},{f2}\n"
 def _write(self,p,lines,headers=None):
  if headers is None:
   headers=("sim_time_s,f1_collision_present,f1_contact_ecs_present,"
    "f1_rod_pair_count,f1_max_rod_contact_force_N,"
    "f2_collision_present,f2_contact_ecs_present,f2_rod_pair_count,"
    "f2_max_rod_contact_force_N\n")
  p.write_text(headers+"".join(lines))
 def test_c16_original_same_sim_frame_bilateral_positive_force(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"same.csv"
   self._write(p,[self._line(65.55+i*.01) for i in range(25)])
   x=require_bilateral_same_ecs_frame_force(p,65.818)
   self.assertTrue(x["both_native_fresh_positive_force"])
   for n in ("finger1","finger2"):
    self.assertGreaterEqual(x["per_finger"][n]["recent_contact_events"],3)
    self.assertGreater(x["per_finger"][n]["max_force_N"],.05)
 def test_zero_force_one_finger_missing_and_stale_are_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"same.csv"
   for lines in ([self._line(64.2)]*5,
                 [self._line(65.7,f1=0.)]*5,
                 [self._line(65.7,c2=0)]*5,
                 [self._line(65.7,f2=float("nan"))]*5,
                 [self._line(66.0)]*5):
    self._write(p,lines)
    self.assertFalse(require_bilateral_same_ecs_frame_force(
     p,65.818)["both_native_fresh_positive_force"])
 def test_missing_force_schema_or_missing_file_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"same.csv"
   self._write(p,[self._line(65.7)]*5,
       headers="sim_time_s,f1_collision_present,f2_collision_present\n")
   self.assertFalse(require_bilateral_same_ecs_frame_force(
    p,65.818)["both_native_fresh_positive_force"])
   self.assertFalse(require_bilateral_same_ecs_frame_force(
    Path(d)/"missing.csv",65.818)["both_native_fresh_positive_force"])
 def test_bad_time_and_cpp_instrumentation_contract(self):
  with self.assertRaises(ValueError):
   require_bilateral_same_ecs_frame_force("/tmp/no-data",float("nan"))
  src=(Path(__file__).resolve().parents[1]/
       "ch07_181_rod_trace"/"rod_trace.cc").read_text()
  self.assertIn("contact.wrench_size()",src)
  self.assertIn("f1_max_rod_contact_force_N",src)
  self.assertIn("f2_max_rod_contact_force_N",src)
  self.assertIn("sync_.flush();",src)
  self.assertNotIn("CreateComponent",src)

if __name__=="__main__":unittest.main()
