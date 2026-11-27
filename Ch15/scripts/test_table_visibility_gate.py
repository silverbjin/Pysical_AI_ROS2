import unittest,math
from table_visibility_gate import VisibilityGate,project
class Tests(unittest.TestCase):
    def test_health_always(self):
        self.assertEqual(VisibilityGate().check(0,full_frame=False,health=False,fresh=False,shift=None),(False,'CAMERA_HEALTH_EXPIRED'))
    def test_blind_then_reacquire(self):
        g=VisibilityGate();self.assertEqual(g.check(0,full_frame=False,health=True,fresh=False,shift=None),(True,'GEOMETRIC_BLIND'))
        self.assertEqual(g.check(5,full_frame=True,health=True,fresh=False,shift=None),(True,'REACQUIRING'))
        self.assertEqual(g.check(5.2,full_frame=True,health=True,fresh=True,shift=.002),(True,'OBSERVED'))
        self.assertEqual(g.check(5.21,full_frame=True,health=True,fresh=False,shift=None),(False,'TARGET_NOT_REACQUIRED'))
    def test_deadline_and_moved(self):
        g=VisibilityGate();g.check(1,full_frame=True,health=True,fresh=False,shift=None)
        self.assertFalse(g.check(1.301,full_frame=True,health=True,fresh=False,shift=None)[0])
        self.assertFalse(g.check(2,full_frame=False,health=True,fresh=True,shift=.03)[0])
    def test_projection(self):
        k=(230.51785523653993,230.51785523653993,159.5,119.5);args=((0,0,.3),(0,0,0,1),(0,0,.25),0,0,k)
        self.assertTrue(project((1,0,.55),*args)['full_frame'])
        self.assertFalse(project((1,-1,.55),*args)['full_frame'])
        with self.assertRaises(ValueError):project((math.nan,0,.55),*args)
if __name__=='__main__':unittest.main()
