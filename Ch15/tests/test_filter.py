import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from filter_experiment import LowPassFilter
class FilterTests(unittest.TestCase):
    def test_first_and_next(self):
        f=LowPassFilter(.2);self.assertEqual(f.filter(5.,1.),5.);self.assertAlmostEqual(f.filter(0.,2.),4.)
    def test_invalid(self):
        for a in (0.,-1.,1.1,float('nan'),'0.2',True):
            with self.assertRaises(ValueError):LowPassFilter(a)
        f=LowPassFilter(.2);f.filter(5.,1.)
        for x in (float('nan'),float('inf'),'0',True,None):
            with self.assertRaises(ValueError):f.filter(x,2.)
            self.assertEqual(f.value,5.)
    def test_rewind(self):
        f=LowPassFilter(.2);f.filter(5.,2.)
        with self.assertRaises(ValueError):f.filter(0.,1.)
        self.assertIsNone(f.value)
        self.assertEqual(f.filter(3.,1.),3.)
if __name__=='__main__':unittest.main()
