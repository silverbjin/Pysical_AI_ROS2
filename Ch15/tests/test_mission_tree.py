import sys,pathlib,unittest,py_trees
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_mission'))
from ch15_mission.mission_tree import create_root
from ch15_mission.recovery import outcome,reset_allowed
from ch15_mission.behaviours import PickObjectBehaviour
S=py_trees.common.Status
keys=('fault_latched','safe_abort','ready','navigate','detect','approach_stand','pick_retract','return_home','place','verify_finish')
def tasks(fault=False):
    return {k:(py_trees.behaviours.Failure(name=k) if k=='fault_latched' and not fault else py_trees.behaviours.Success(name=k)) for k in keys}
class Tests(unittest.TestCase):
    def test_profiles(self):
        for profile,count in [('mock',8),('physical_basic',5)]:
            root=create_root(profile,tasks());self.assertEqual(len(root.children[1].children),count);root.tick_once();self.assertEqual(root.status,S.SUCCESS)
        with self.assertRaises(ValueError):create_root('physical_full',tasks())
    def test_safety_success_not_mission(self):
        r=create_root('mock',tasks(True));r.tick_once();self.assertEqual(r.status,S.SUCCESS);self.assertEqual(outcome(True,False,True),'ABORTED');self.assertEqual(outcome(True,False,False),'ERROR')
        self.assertFalse(reset_allowed(True,False,True,True,False));self.assertFalse(reset_allowed(False,True,True,True,False))
    def test_invalid_target_no_send(self):
        class Supervisor:
            def send(self,g):raise AssertionError('invalid target sent')
        b=PickObjectBehaviour('pick',Supervisor(),lambda:None);b.tick_once();self.assertEqual(b.status,S.FAILURE)
if __name__=='__main__':unittest.main()
