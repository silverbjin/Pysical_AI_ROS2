import sys,unittest,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from clock_cross_layer_analyzer import bounds,choose,analyze_phase,matched_bounds

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
    def matched_fixture(self, step=False):
        # Both clocks share a 9% relative RAW/monotonic rate. Same-kind comparison must not reject it.
        rows=[]
        for base in (0, 610_000_000_000):
            for i in range(12):
                m=base+i*50_000_000
                raw=round(m*1.09)
                rt=m+10**18+(3_000_000_000 if step and base and i>=5 else 0)
                rows.append(dict(monotonic_ns=m,reads={'monotonic_raw':dict(m0=m,m1=m,value_ns=raw),'realtime':dict(m0=m,m1=m,value_ns=rt)}))
        anchors=[]
        for phase,base in [('before',0),('after',610_000_000_000)]:
            m=base+250_000_000
            anchors.append(dict(phase=phase,qpc_before_ns=m-10_000_000,qpc_after_ns=m+10_000_000,guest=dict(monotonic_ns=m,reads={'monotonic_raw':{'value_ns':round(m*1.09)},'realtime':{'value_ns':m+10**18}})))
        return anchors,rows
    def test_same_kind_no_false_docker_drift(self):
        a,h=self.matched_fixture()
        r=matched_bounds(a,h,'monotonic_raw')
        self.assertEqual(r['reference_clock'],'monotonic_raw')
        self.assertLess(r['lower_ppm'],0);self.assertGreater(r['upper_ppm'],0)
        self.assertLess(r['upper_ppm'],1000)
        self.assertGreater(bounds(a[0],a[1],lambda g:g['reads']['monotonic_raw']['value_ns'])['lower_ppm'],80000)
    def test_step_inside_anchor_inconclusive(self):
        a,h=self.matched_fixture(step=True)
        self.assertIsNone(matched_bounds(a,h,'realtime'))
    def test_missing_host_bracket(self):
        a,h=self.matched_fixture()
        self.assertIsNone(matched_bounds(a,h[:12],'monotonic_raw'))
    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            r=analyze_phase(Path(d));self.assertEqual(r['layers']['host']['quality'],'NOT_AVAILABLE');self.assertEqual(r['status'],'REVIEW_REQUIRED')

if __name__=='__main__': unittest.main()
