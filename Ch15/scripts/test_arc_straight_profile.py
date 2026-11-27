import math, unittest
from arc_straight_profile import *
class ArcTests(unittest.TestCase):
    def test_local_frame(self):
        x,y,h=local((1.,3.,math.pi/2),(1.,2.,math.pi/2))
        self.assertAlmostEqual(x,1);self.assertAlmostEqual(y,0);self.assertAlmostEqual(h,0)
    def test_arc(self):
        self.assertEqual(arc_command((0,0,0)),(.008,-.10))
        x,y=arc_point(ANGLE)
        self.assertTrue(arc_ready((x,y,-ANGLE)))
        self.assertEqual(arc_command((x,y,-ANGLE)),(0.,0.))
        self.assertIsNone(arc_command((.2,.2,-.2)))
    def test_straight(self):
        x,y=arc_point(ANGLE)
        self.assertIsNotNone(straight_command((x,y,-ANGLE)))
        g=final_target();self.assertEqual(straight_command(g),(0.,0.))
        self.assertTrue(final_ready(g));self.assertFalse(final_ready((g[0]+.02,g[1],g[2])))
        self.assertIsNone(straight_command((g[0],g[1],g[2]+.2)))
if __name__=='__main__':unittest.main()
