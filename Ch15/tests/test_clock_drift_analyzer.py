import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from clock_drift_analyzer import analyze


def rows(ppm=0,step=0,missing=False,gap=False,bracket=1000,sim=False):
    out=[]
    for i in range(601):
        t=i*50_000_000
        if gap and 200<=i<240:
            continue
        def r(v): return dict(m0=t,m1=t+bracket,value_ns=v)
        d={'realtime':r(t+10**18+(step if i>=300 else 0)), 'monotonic_raw':r(t+int(t*ppm/1e6)), 'ros_time':r(t)}
        if missing and i==200: d.pop('realtime')
        out.append(dict(scope='fixture',monotonic_ns=t+bracket,reads=d,sim_time=sim))
    return out


class Drift(unittest.TestCase):
    def test_normal(self):
        a=analyze(rows()); self.assertEqual(a['quality'],'COMPLETE'); self.assertAlmostEqual(a['clocks']['monotonic_raw']['median_clean_ppm'],0)
    def test_drift(self):
        self.assertAlmostEqual(analyze(rows(90962))['clocks']['monotonic_raw']['median_clean_ppm'],90962,places=1)
    def test_forward(self):
        self.assertEqual(analyze(rows(step=2_940_000_000))['clocks']['realtime']['events'][0]['kind'],'FORWARD')
    def test_backward(self):
        self.assertEqual(analyze(rows(step=-2_940_000_000))['clocks']['realtime']['events'][0]['kind'],'BACKWARD')
    def test_missing(self):
        self.assertEqual(analyze(rows(missing=True))['clocks']['realtime']['quality'],'PARTIAL')
    def test_gap(self):
        a=analyze(rows(90962,gap=True)); self.assertEqual(a['clocks']['monotonic_raw']['events'][0]['kind'],'COVERAGE_GAP')
    def test_bracket(self):
        self.assertEqual(analyze(rows(bracket=6_000_000))['quality'],'PARTIAL')
    def test_sim(self):
        self.assertIsNone(analyze(rows(sim=True))['clocks']['ros_time']['total_rate'])
    def test_order(self):
        with self.assertRaises(ValueError): analyze(list(reversed(rows())))
    def test_compound(self):
        a=analyze(rows(90962,step=2_940_000_000,gap=True)); self.assertEqual([e['kind'] for e in a['clocks']['realtime']['events']],['COVERAGE_GAP','FORWARD'])
    def test_empty(self):
        self.assertEqual(analyze([])['quality'],'INSUFFICIENT')

if __name__=='__main__': unittest.main()
