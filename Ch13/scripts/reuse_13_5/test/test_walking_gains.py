import ast,importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('reproduction',ROOT/'Ch13/scripts/reuse_13_5/reproduce_upstream.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
ORIGINAL=(ROOT.parent/'upstream-iit-locomanipulation-d010212/deploy/play_mujoco.py').read_text()
class WalkingGainTests(unittest.TestCase):
    def gains_between_policy_ticks(self,active):
        tree=ast.parse(mod.consistent_walking_run_source(ORIGINAL))
        branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Attribute) and n.test.values[0].attr=='isRLActivated')
        policy=SimpleNamespace(Kp_walking=20.,Kd_walking=1.5,Kp_stand_up_and_down=50.,Kd_stand_up_and_down=5.)
        platform=SimpleNamespace(console=SimpleNamespace(isRLActivated=active),locomotion_policy=policy)
        statements=ast.Module(body=branch.orelse,type_ignores=[])
        exec(compile(statements,'actual_upstream_else_branch','exec'),{'self':platform})
        return platform.Kp_legs,platform.Kd_legs
    def test_active_policy_holds_walking_gains_between_inference_ticks(self):
        self.assertEqual(self.gains_between_policy_ticks(True),(20.,1.5))
    def test_inactive_policy_keeps_existing_stand_gains(self):
        self.assertEqual(self.gains_between_policy_ticks(False),(50.,5.))
    def test_unknown_source_is_rejected_instead_of_silent_partial_patch(self):
        with self.assertRaises(ValueError):mod.consistent_walking_run_source('def run(self):\n    pass\n')
if __name__=='__main__':unittest.main()
