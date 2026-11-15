"""TDD before one public Gazebo experiment. No accepted gate relaxation."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_181_ecm_contact_boundary import classify_same_ecs_frame as check

class ECSContactSameFrameTDD(unittest.TestCase):
    def test_original_195_ghost_event_is_strict_red(self):
        self.assertEqual(check(59.0,.0357,True,1,59.0),
                         'ECS_SAME_FRAME_PHYSICALLY_IMPOSSIBLE_CONTACT')
    def test_contact_component_absence_is_unknown_not_negative(self):
        self.assertEqual(check(59.0,.075,False,-1,float('nan')),
                         'CONTACT_ECS_COMPONENT_NOT_PRESENT_UNOBSERVED')
    def test_async_or_stale_contact_is_not_labeled_solver_bug(self):
        self.assertEqual(check(59.0,.075,True,1,58.0),
                         'ECS_CONTACT_COMPONENT_STALE_OR_FUTURE')
    def test_overlap_does_not_prove_contact(self):
        self.assertEqual(check(59.0,-.001,True,1,59.0),
                         'GEOMETRY_BOUNDS_OVERLAP_CONTACT_STILL_UNPROVEN')
    def test_no_pair_is_not_positive_contact(self):
        self.assertEqual(check(59.0,.04,True,0,float('nan')),
                         'NO_CONTACT_PAIR_ECS')
    def test_nan_and_bad_params_fail_closed(self):
        for args in ((59,float('nan'),True,1,59),(-1,.01,True,1,0),(59,.01,1,1,59)):
            with self.assertRaises(ValueError):check(*args)
if __name__=='__main__':unittest.main()
