import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_worldpose_source_contract import classify_pose_provenance as c
class NativePoseComponentProvenanceTDD(unittest.TestCase):
 def test_readonly_worldpose_component_explains_prior_finger_delta(self):
  self.assertEqual(c(.0675,.00002,True),'HELPER_RELATIVE_CHAIN_DIFFERS_FROM_LIVE_WORLDPOSE')
 def test_unknown_if_world_component_missing(self):
  self.assertEqual(c(.0675,float('nan'),False),'WORLD_POSE_COMPONENT_ABSENT_UNDETERMINED')
 def test_differing_worldpose_never_promoted(self):
  self.assertEqual(c(.0001,.060,True),'WORLDPOSE_COMPONENT_DIFFERS_FROM_HELPER_AND_SCENE')
  self.assertEqual(c(.0675,.06,True),'BOTH_DIFFER_FROM_SCENE_SOURCE_UNDETERMINED')
 def test_zero_gap_is_consistent_only(self):
  self.assertEqual(c(.0001,.0001,True),'POSE_SOURCES_CONSISTENT_WITHIN_SCOPE')
 def test_bad_or_nonfinite_fails_closed(self):
  for args in ((float('nan'),0,True),(-.1,0,True),(.1,0,1),(.1,-.1,True)):
   with self.assertRaises(ValueError):c(*args)
if __name__=='__main__':unittest.main()
