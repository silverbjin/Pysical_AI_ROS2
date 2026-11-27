import sys,pathlib,unittest
from dataclasses import replace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_mission'))
from ch15_mission.blackboard_context import BlackboardContext,Target
class Tests(unittest.TestCase):
    def setUp(self):
        self.b=BlackboardContext('m',1);self.b.clock(1000000000,1.)
        self.good=Target('m',1,'MOCK','red_cube','map',950000000,(1.,0.,0.),(0.,0.,0.,1.),'GRASP_POSE',1.)
    def test_normal(self):self.assertTrue(self.b.write_target(self.good,True,1.));self.assertEqual(self.b.read(1.),self.good)
    def test_negative_ten(self):
        cases=[('stale',replace(self.good,stamp_ns=699999999),True),('future',replace(self.good,stamp_ns=1000000001),True),('zero',replace(self.good,stamp_ns=0),True),('frame',replace(self.good,frame='odom'),True),('tf',self.good,False),('mission',replace(self.good,mission_id='old'),True),('epoch',replace(self.good,epoch=0),True),('nonfinite',replace(self.good,position=(float('nan'),0.,0.)),True)]
        for label,t,tf in cases:
            with self.subTest(label=label):
                self.assertTrue(self.b.write_target(self.good,True,1.));self.assertFalse(self.b.write_target(t,tf,1.));self.assertIsNone(self.b.read(1.))
        self.assertTrue(self.b.write_target(self.good,True,1.));self.b.clock(1000000000,1.21);self.assertFalse(self.b.write_target(self.good,True,1.21));self.assertIsNone(self.b.read(1.21))
        self.b.clock(1100000000,1.22);self.b.clock(1000000000,1.23);self.assertFalse(self.b.write_target(self.good,True,1.23));self.assertIsNone(self.b.read(1.23))
    def test_settle_and_receipt(self):
        self.b.mark_settled();self.assertFalse(self.b.write_target(self.good,True,1.))
        self.b.clock(1100000000,1.1);new=replace(self.good,stamp_ns=1050000000,received=1.1)
        self.assertTrue(self.b.write_target(new,True,1.1));self.assertIsNone(self.b.read(1.41))
if __name__=='__main__':unittest.main()
