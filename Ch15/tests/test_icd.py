import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_interfaces'
class ICDTests(unittest.TestCase):
    def test_interface_count(self):
        expected={'action/PickObject.action','action/PlaceObject.action','srv/SwitchGait.srv','msg/MissionStatus.msg','msg/TargetObservation.msg','msg/SafetyState.msg','msg/ReadyState.msg','msg/MissionEvent.msg'}
        actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.suffix in ('.action','.srv','.msg')}
        self.assertEqual(actual,expected)
        cmake=(ROOT/'CMakeLists.txt').read_text()
        for p in expected:self.assertIn('"'+p+'"',cmake)
    def test_pick_contract(self):
        self.assertEqual((ROOT/'action/PickObject.action').read_text().splitlines(),['string object_class','geometry_msgs/PoseStamped target_pose','float32 timeout_sec','---','bool success','string error_message','float32 execution_time','---','string current_state','float32 distance_remaining'])
if __name__=='__main__':unittest.main()
