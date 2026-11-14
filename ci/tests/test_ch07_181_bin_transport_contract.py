#!/usr/bin/env python3
import pathlib,sys,unittest,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from ch07_181_bin_transport_contract import (
 corrected_high_target,custody_offset,custody_drift,high_arrival_valid,
 pre_release_valid,LOWER_WRIST_Z)
class WorldPoseTransportTDD(unittest.TestCase):
 def test_world_pose_based_high_wrist_target(self):
  p=corrected_high_target((.528212,-.006809,2.07042))
  self.assertAlmostEqual(p[0],.501788)
  self.assertAlmostEqual(p[1],.256809)
  self.assertEqual(p[2],1.96)
  self.assertEqual(LOWER_WRIST_Z,1.72)
 def test_missing_bounded_or_unheld_rod_refused(self):
  for p in ((-.4,-.4,2.07),(.53,0,1.80),(float("nan"),0,2.07)):
   with self.subTest(p=p),self.assertRaises(ValueError):
    corrected_high_target(p)
 def test_original_transfer_slip_proven(self):
  offset=custody_offset((.528385,-.006804,2.07032),(.537285,-.009753,2.048886))
  self.assertGreater(custody_drift((.642772,.088063,1.83891),
                    (.563734,.269913,1.82261),offset),.10)
 def test_original_pre_release_cannot_open(self):
  self.assertFalse(pre_release_valid((.642772,.088063,1.83891),.18))
 def test_high_and_low_guards_distinct(self):
  self.assertTrue(high_arrival_valid((.552,.248,2.063),.012))
  self.assertFalse(pre_release_valid((.552,.248,2.063),.012))
  self.assertTrue(pre_release_valid((.552,.248,1.83),.012))
  self.assertFalse(pre_release_valid((.552,.248,1.70),.012))
  self.assertFalse(pre_release_valid((.552,.248,1.83),.05))
if __name__=="__main__":unittest.main()
