from pathlib import Path
import sys,unittest,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.state_adapter import adapt
class StateTests(unittest.TestCase):
    def state(self,q=None,v=None):
        return adapt(q or [2,3,.3,1,0,0,0]+list(range(20)),v or [1,0,0,0,0,0]+list(range(20)),['j'+str(i) for i in range(20)],2_000_000_000)
    def test_uses_engine_pose_and_joint_order(self):
        s=self.state();self.assertEqual(s['position'],(2,3,.3));self.assertEqual(list(s['joint_positions']),list(range(20)));self.assertEqual(s['stamp_ns'],2_000_000_000)
    def test_heading_projection_preserves_actual_body_rotation(self):
        c=math.sqrt(.5);q=[2,3,.3,c,0,0,c]+[0]*20;s=self.state(q)
        self.assertAlmostEqual(s['yaw'],math.pi/2);self.assertAlmostEqual(s['nav_linear'][1],-1);self.assertAlmostEqual(s['body_linear'][1],-1);self.assertAlmostEqual(s['residual_quat_xyzw'][3],1)
    def test_pitch_and_vertical_state_not_erased(self):
        q=[2,3,.3,math.cos(math.pi/12),0,math.sin(math.pi/12),0]+[0]*20
        v=[1,0,0,0,0,3]+[0]*20;s=self.state(q,v)
        self.assertAlmostEqual(s['body_linear'][0],math.sqrt(3)/2);self.assertAlmostEqual(s['body_linear'][2],.5);self.assertAlmostEqual(s['nav_yaw_rate'],2*math.sqrt(3));self.assertAlmostEqual(s['residual_quat_xyzw'][1],math.sin(math.pi/12))
    def test_nonfinite_quaternion_and_bad_dimensions_rejected(self):
        for q in [[0]*27,[0,0,.3,float('nan'),0,0,0]+[0]*20,[0]*3]:
            with self.assertRaises(ValueError):self.state(q)
if __name__=='__main__':unittest.main()
