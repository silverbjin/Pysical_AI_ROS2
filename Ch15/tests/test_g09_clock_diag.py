import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from clock_diag import compare,summarize,sample
def row(t,offset=0,bracket=1000,sim=False,ros_offset=None,boot_offset=0):
    def r(o):return dict(m0=t,m1=t+bracket,value_ns=t+o)
    return dict(scope='fixture',monotonic_ns=t+bracket,sim_time=sim,reads={'realtime':r(offset),'system_time':r(offset),'ros_time':r(offset if ros_offset is None else ros_offset),'boottime':r(boot_offset),'steady_time':r(0)})
class ClockDiag(unittest.TestCase):
    def test_original_owner_interval(self):
        a=row(567027120014,1795771275342205517-567027120014)
        b=row(567127201222,1795771278369595522-567127201222)
        d=compare(a,b,'realtime')
        self.assertEqual(d['kind'],'FORWARD')
        self.assertLessEqual(d['offset_change_lower_ns'],2927308797)
        self.assertGreaterEqual(d['offset_change_upper_ns'],2927308797)
        self.assertTrue(summarize([a,b])['observed_system_or_ros_step'])
    def test_backward(self):
        self.assertEqual(compare(row(0),row(50_000_000,-500_000_000),'realtime')['kind'],'BACKWARD')
    def test_deschedule_not_step(self):
        r=summarize([row(0),row(3_000_000_000)])
        self.assertEqual(r['quality'],'PARTIAL')
        self.assertEqual(r['result'],'INCONCLUSIVE')
        self.assertFalse(r['observed_system_or_ros_step'])
    def test_uncertain_bracket(self):
        r=summarize([row(0),row(50_000_000,300_000_000,bracket=10_000_000)])
        self.assertEqual(r['result'],'INCONCLUSIVE')
        self.assertFalse(r['observed_system_or_ros_step'])
    def test_ambiguous_threshold(self):
        self.assertEqual(compare(row(0),row(50_000_000,100_000_000),'realtime')['kind'],'AMBIGUOUS_THRESHOLD')
    def test_sim_not_system(self):
        r=summarize([row(0,sim=True,ros_offset=0),row(50_000_000,sim=True,ros_offset=-500_000_000)])
        self.assertFalse(r['observed_system_or_ros_step'])
        self.assertEqual(r['counts']['ros_time']['SIM_OR_UNKNOWN_ROS_CLOCK'],1)
    def test_boottime_separate(self):
        r=summarize([row(0),row(50_000_000,boot_offset=500_000_000)])
        self.assertFalse(r['observed_system_or_ros_step'])
        self.assertEqual(r['counts']['boottime']['FORWARD'],1)
    def test_insufficient(self):self.assertEqual(summarize([row(0)])['result'],'INCONCLUSIVE')
    def test_sample(self):
        a=sample()
        self.assertIn('realtime',a['reads'])
        self.assertLessEqual(a['reads']['realtime']['m0'],a['reads']['realtime']['m1'])
if __name__=='__main__':unittest.main()
