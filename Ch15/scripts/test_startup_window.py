import unittest
from startup_window import StartupWindow
class Tests(unittest.TestCase):
    def test_healthy(self):
        g=StartupWindow()
        for i in range(101):
            ok=g.observe(i*.02,tuple([1+i*20_000_000]*3),True)
            self.assertEqual(ok,i==100)
    def test_recorded_gap(self):
        g=StartupWindow()
        for i in range(100):self.assertFalse(g.observe(i*.02,tuple([1+i*20_000_000]*3),True))
        # Recorded 360ms engine-publication gap. Cached stamps cannot admit.
        self.assertFalse(g.observe(2.340347897,tuple([1+99*20_000_000]*3),True))
        self.assertEqual(g.resets,1)
    def test_bad_readiness(self):
        g=StartupWindow();g.observe(0,(1,1,1),True)
        self.assertFalse(g.observe(.02,(2,2,2),False))
        self.assertEqual(g.resets,1)
if __name__=='__main__':unittest.main()
