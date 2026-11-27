import unittest,math
from heading_first_profile import stage,aligned,straight,corridor,final,yaw_error

class TestProfile(unittest.TestCase):
    def test_stage(self):
        self.assertAlmostEqual(stage((2.2,1,0))[0],1.8)
        self.assertAlmostEqual(stage((0,0,math.pi/2))[1],-.4)
        self.assertAlmostEqual(yaw_error(math.pi-.01,-math.pi+.01),.02)
    def test_straight(self):
        g=(2.2,1.,0.);p=(1.8,1.01,.03)
        self.assertTrue(aligned(p,g))
        path=straight(p,g)
        self.assertEqual(path[-1],g)
        self.assertTrue(all(x[2]==0 for x in path))
        self.assertTrue(all(math.dist(a[:2],b[:2])<=.01000001 for a,b in zip(path,path[1:])))
        for bad in [(1.8,1.04,0),(1.8,1,.07),(2.1,1,0),(float('nan'),1,0)]:
            self.assertFalse(aligned(bad,g))
            with self.assertRaises(ValueError):straight(bad,g)
    def test_limits(self):
        g=(2.2,1.,0.)
        self.assertTrue(corridor((2.,1.04,.1),g))
        for p in [(2.,1.06,0),(2.,1.,.13),(2.23,1.,0),(1.7,1.,0),(2.,float('nan'),0)]:
            self.assertFalse(corridor(p,g))
        self.assertTrue(final((2.21,1.,.05),g))
        self.assertFalse(final((2.216,1.,0),g))
        self.assertFalse(final((2.2,1.,.061),g))
if __name__=='__main__':unittest.main()
