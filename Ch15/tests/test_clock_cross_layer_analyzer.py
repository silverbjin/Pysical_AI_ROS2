import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from clock_cross_layer_analyzer import bounds,choose,analyze_phase

class CrossLayer(unittest.TestCase):
    def anchor(self,phase,q,g,delay=10_000_000):
        return dict(phase=phase,qpc_before_ns=q,qpc_after_ns=q+delay,guest={'monotonic_ns':g})
    def test_different_epochs(self):
        a=self.anchor('before',10**18,10**12); b=self.anchor('after',10**18+600*10**9,10**12+600*10**9)
        r=bounds(a,b,lambda g:g['monotonic_ns']);self.assertLess(r['lower_ppm'],0);self.assertGreater(r['upper_ppm'],0)
    def test_slow_guest(self):
        a=self.anchor('before',10**18,10**12); b=self.anchor('after',10**18+600*10**9,10**12+550*10**9)
        r=bounds(a,b,lambda g:g['monotonic_ns']);self.assertLess(r['upper_ppm'],-80_000)
    def test_rtt_selection(self):
        a=self.anchor('before',0,10,500_000_001);b=self.anchor('before',0,10,20_000_000)
        self.assertEqual(choose([a,b],'before'),b);self.assertIsNone(choose([a],'before'))
    def test_overlap(self):
        a=self.anchor('before',0,10);b=self.anchor('after',1,11);self.assertIsNone(bounds(a,b,lambda g:g['monotonic_ns']))
    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            r=analyze_phase(Path(d));self.assertEqual(r['layers']['host']['quality'],'NOT_AVAILABLE');self.assertEqual(r['status'],'REVIEW_REQUIRED')

if __name__=='__main__': unittest.main()
