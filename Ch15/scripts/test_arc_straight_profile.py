import math, unittest
from arc_straight_profile import *
class ArcTests(unittest.TestCase):
    def test_local_frame(self):
        x,y,h=local((1.,3.,math.pi/2),(1.,2.,math.pi/2))
        self.assertAlmostEqual(x,1);self.assertAlmostEqual(y,0);self.assertAlmostEqual(h,0)
    def test_arc(self):
        self.assertEqual(arc_command((0,0,0)),(.0125,-.10))
        x,y=arc_point(ANGLE)
        self.assertTrue(arc_ready((x,y,-ANGLE)))
        self.assertEqual(arc_command((x,y,-ANGLE)),(0.,0.))
        self.assertIsNone(arc_command((.2,.2,-.2)))
    def test_radial_feedback(self):
        theta=.8
        x,y=arc_point(theta)
        # Inward displacement (toward circle centre) with same heading.
        inside=(x-.02*math.sin(theta),y-.02*math.cos(theta),-theta)
        nominal=arc_command((x,y,-theta));corrected=arc_command(inside)
        self.assertGreater(corrected[0],nominal[0])
        self.assertGreater(corrected[1],nominal[1])
        outside=(x+.02*math.sin(theta),y+.02*math.cos(theta),-theta)
        self.assertLess(arc_command(outside)[0],nominal[0])
        self.assertGreaterEqual(corrected[0],0)
        self.assertLessEqual(corrected[0],.018)
        self.assertGreaterEqual(corrected[1],-.10)
        self.assertLessEqual(corrected[1],-.07)
        self.assertIsNone(arc_command((float('nan'),0,0)))
    def test_straight(self):
        x,y=arc_point(ANGLE)
        self.assertIsNotNone(straight_command((x,y,-ANGLE)))
        g=final_target();self.assertEqual(straight_command(g),(0.,0.))
        self.assertTrue(final_ready(g));self.assertFalse(final_ready((g[0]+.02,g[1],g[2])))
        self.assertIsNone(straight_command((g[0],g[1],g[2]+.2)))
    def test_straight_slip_and_stop_compensation(self):
        x,y,h=final_target()
        def pose(along,lat,heading=0):
            c,s=math.cos(h),math.sin(h)
            return x-along*c+lat*s,y-along*s-lat*c,h-heading
        early=straight_command(pose(.15,0))
        near=straight_command(pose(.015,0))
        self.assertGreater(early[1],near[1])
        self.assertGreater(near[1],.012)
        self.assertGreaterEqual(early[1],-.05)
        self.assertLessEqual(early[1],.05)
        self.assertEqual(straight_command(pose(.006,0)),(0.,0.))
        self.assertFalse(final_ready(pose(0,.016)))
        self.assertFalse(final_ready(pose(0,0,.061)))
if __name__=='__main__':unittest.main()
