import math
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_adapters'))
from ch15_adapters.contracts import valid_pose, valid_timeout, ReadinessGate, SafetyGate

class ContractTests(unittest.TestCase):
    def test_pose(self):
        self.assertTrue(valid_pose('map',[1.,2.,0.],[0.,0.,0.,1.]))
        for frame,p,q in [('',[0.,0.,0.],[0.,0.,0.,1.]),('map',[math.nan,0.,0.],[0.,0.,0.,1.]),('map',[0.,0.,0.],[0.,0.,0.,0.])]:
            self.assertFalse(valid_pose(frame,p,q))
    def test_timeout(self):
        self.assertTrue(valid_timeout(10.))
        for x in [0.,10.01,math.inf,math.nan,-1.,True]: self.assertFalse(valid_timeout(x))
    def test_readiness(self):
        for missing in ['server','tf','sensor','lifecycle','heartbeat','owner']:
            gate=ReadinessGate()
            self.assertFalse(gate.sample([missing])); self.assertFalse(gate.sample([])); self.assertFalse(gate.sample([])); self.assertTrue(gate.sample([])); self.assertFalse(gate.sample([missing]))
    def test_safety(self):
        gate=SafetyGate()
        self.assertTrue(gate.blocked(0.,True,True))
        gate.heartbeat(False,1.); self.assertFalse(gate.blocked(1.1,True,True))
        self.assertTrue(gate.blocked(1.151,True,True))
        gate.heartbeat(False,1.2); self.assertTrue(gate.blocked(1.2,True,True))
        gate=SafetyGate(); gate.heartbeat(False,1.); self.assertTrue(gate.blocked(1.,False,True))
        gate.heartbeat(True,1.1); gate.heartbeat(False,1.2); self.assertTrue(gate.blocked(1.2,True,True))
        self.assertFalse(gate.reset(1.2,True,True,False)); self.assertTrue(gate.reset(1.2,True,True,True)); self.assertFalse(gate.blocked(1.2,True,True))
if __name__=='__main__': unittest.main()
