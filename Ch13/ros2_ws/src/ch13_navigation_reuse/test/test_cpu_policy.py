"""Runtime scheduling must preserve pinned actor outputs, not retrain them."""
import unittest,time,json
from pathlib import Path
import numpy as np,onnxruntime as ort
class CpuPolicyTests(unittest.TestCase):
 def test_cpu_session_matches_original_actor(self):
  from ch13_navigation_reuse.cpu_policy import cpu_session
  root=Path(__file__).resolve().parents[5]
  policy=root.parent/'upstream-iit-locomanipulation-d010212/tested_policies/arm_moving_clock/exported/policy.onnx'
  original=ort.InferenceSession(str(policy));bounded=cpu_session(str(policy));x=np.random.default_rng(135).normal(0,.2,(1,300)).astype(np.float32)
  expected=original.run(None,{'obs':x});actual=bounded.run(None,{'obs':x})
  np.testing.assert_allclose(actual[0],expected[0],atol=1e-6,rtol=1e-6)
  options=bounded.get_session_options();self.assertEqual(options.intra_op_num_threads,1);self.assertEqual(options.inter_op_num_threads,1)
