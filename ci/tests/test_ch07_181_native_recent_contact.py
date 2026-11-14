#!/usr/bin/env python3
import pathlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_native_recent_contact import (
 recent_native_finger_rod_contact,require_bilateral_pre_release_contact)
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
if __name__=="__main__":unittest.main()
