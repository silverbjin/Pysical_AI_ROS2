import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from ch15_simulation.joint_tuner import RealTimeTuner,torque
from pid_experiment import summarize,FIELDS
class JointTests(unittest.TestCase):
    def test_atomic_reject(self):
        t=RealTimeTuner();old=t.snapshot
        for p in ({'kp':float('nan'),'kd':1},{'kp':61,'kd':1},{'kp':2,'kd':21},{'kp':'1','kd':2},{'kp':True,'kd':1},{'kp':2,'kd':float('inf')},{'kp':2},{'kp':-1,'kd':1}):
            with self.assertRaises(ValueError):t.configure(p)
            self.assertIs(t.snapshot,old)
        self.assertEqual(t.configure({'kp':60,'kd':20}).kp,60.)
    def test_trial(self):
        t=RealTimeTuner()
        with t.trial() as g:
            with self.assertRaises(RuntimeError):t.configure({'kp':1,'kd':1})
            self.assertIs(t.snapshot,g)
        self.assertFalse(t.active)
    def test_torque(self):
        t=RealTimeTuner({'kp':60,'kd':20})
        self.assertEqual(torque(t.snapshot,-2.,-2.),(220.,60.))
        with self.assertRaises(ValueError):torque(t.snapshot,float('nan'),0.)
    def test_invalid_response(self):
        with self.assertRaises(ValueError):summarize([])
        valid=[(i,i*.005,1.,0.,1.,0.,0.,0.,0.,10) for i in range(1,801)]
        self.assertEqual(summarize(valid)['samples'],800)
        bad=list(valid);bad[100]=tuple([101,.2,1.,0.,1.,0.,0.,0.,0.,10])
        with self.assertRaises(ValueError):summarize(bad)
        bad=list(valid);bad[100]=tuple([101,.505,float('nan'),0.,1.,0.,0.,0.,0.,10])
        with self.assertRaises(ValueError):summarize(bad)
        bad=list(valid);bad[100]=tuple([101,.505,2.1,0.,1.,0.,0.,0.,0.,10])
        with self.assertRaises(ValueError):summarize(bad)
if __name__=='__main__':unittest.main()
