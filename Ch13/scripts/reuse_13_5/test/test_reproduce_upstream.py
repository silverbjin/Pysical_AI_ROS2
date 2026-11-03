import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np
MODULE=Path(__file__).resolve().parents[1]/'reproduce_upstream.py'
spec=importlib.util.spec_from_file_location('reproduction',MODULE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ArmReferenceTests(unittest.TestCase):
    # Failure caught: a view into qpos turns engine motion into a new target.
    def test_engine_motion_does_not_rewrite_commanded_arm_target(self):
        qpos=np.arange(27,dtype=float)
        p=SimpleNamespace(desired_joint_pos_arm=qpos[19:25])
        module.freeze_arm_reference(p)
        qpos[19]=1000
        self.assertEqual(p.desired_joint_pos_arm[0],19)
    # Failure caught: correction must not alter current physics state or target value.
    def test_snapshot_preserves_all_target_values_and_engine_state(self):
        qpos=np.arange(27,dtype=float)
        p=SimpleNamespace(desired_joint_pos_arm=qpos[19:25])
        module.freeze_arm_reference(p)
        np.testing.assert_array_equal(p.desired_joint_pos_arm,[19,20,21,22,23,24])
        np.testing.assert_array_equal(qpos,np.arange(27,dtype=float))
if __name__=='__main__':unittest.main()
