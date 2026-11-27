import copy,json,sys,tempfile,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'python'),str(root/'scripts')]
from clock_failure_classifier import classify,inspect_archive
from owner_runner import pack
def fixture():
    # Minimal exact witness values transcribed from independently verified R01 owner RED.
    owner={'result':'FAIL','exit_code':1}
    rec={'mode':'F03_transient','result':'FAIL','terminal':'ABORTED'}
    src=[{'kind':'publish_enter','wall_ns':567027120014,'stamp_ns':1795771275342205517},{'kind':'publish_enter','wall_ns':567127201222,'stamp_ns':1795771278369595522}]
    wd=[{'kind':'scan','wall_ns':567027506664,'stamp_ns':1795771275342205517,'valid':True},{'kind':'watchdog','wall_ns':567062125864,'age_s':.034413590999974986,'source_stamp_ns':1795771275342205517,'first_latch':True}]
    events=[{'event':'RECOVERY_ATTEMPT','steady_ns':566402585664,'ros_ns':1795771274717676575},{'event':'FAULT','steady_ns':567102006914,'ros_ns':1795771278344414597,'detail':{'reason':'readiness_or_safety_lost'}},{'event':'END','steady_ns':567102690105,'ros_ns':1795771278345093938,'detail':{'state':'ABORTED','all_terminal':True}}]
    return owner,rec,src,wd,events
class ClockClassification(unittest.TestCase):
    def test_owner_red(self):
        r=classify(*fixture())
        self.assertEqual(r['classification'],'CLOCK_DISCONTINUITY_CORRELATED')
        self.assertEqual(r['source_excess_ns'],2927308797)
        self.assertEqual(r['mission_excess_ns'],2927316772)
        self.assertEqual(r['owner_verdict'],'FAIL')
        self.assertFalse(r['automatic_retry']);self.assertFalse(r['safety_override'])
        self.assertFalse(r['direct_clock_step_observed'])
    def test_no_cross_witness(self):
        a=list(fixture());a[4][1]['ros_ns']-=2927316772
        self.assertEqual(classify(*a)['classification'],'FAILURE_UNRESOLVED')
    def test_no_native_freshness(self):
        a=list(fixture());a[3][1]['age_s']=1.1
        self.assertEqual(classify(*a)['classification'],'FAILURE_UNRESOLVED')
    def test_missing(self):
        a=list(fixture());a[2]=[]
        self.assertEqual(classify(*a)['classification'],'INSUFFICIENT_EVIDENCE')
    def test_expected_abort_and_outer_failure(self):
        a=list(fixture());a[1].update(mode='F06',result='PASS')
        self.assertEqual(classify(*a)['classification'],'RECORD_PASS_PROFILE_NOT_ACCEPTED')
        a[0]['result']='PASS'
        self.assertEqual(classify(*a)['classification'],'RECORD_PASS')
    def test_correlate_direct_only_matching_window(self):
        d={'events':[dict(clock='system_time',kind='FORWARD',window_start_ns=567027120014,window_end_ns=567127201222,offset_change_lower_ns=2927308000,offset_change_upper_ns=2927309000),dict(clock='ros_time',kind='FORWARD',window_start_ns=1,window_end_ns=2,offset_change_lower_ns=2927308000,offset_change_upper_ns=2927309000)]}
        self.assertEqual(classify(*fixture(),d)['direct_container_clocks'],['system_time'])
    def test_archive_roundtrip(self):
        owner,rec,src,wd,events=fixture()
        with tempfile.TemporaryDirectory() as d:
            run=Path(d)/'run';case=run/'faults/F03_transient';(case/'executor').mkdir(parents=True)
            for path,obj in [(run/'owner-result.json',owner),(run/'source-receipt.json',{}),(run/'environment.json',{}),(run/'process_audit.json',{}),(case/'record_result.json',rec),(case/'scan_source_trace.json',{'events':src}),(case/'watchdog_native_trace.json',{'events':wd})]:
                path.write_text(json.dumps(obj))
            (case/'executor/mission-events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events))
            pack(run)
            arc=run.parent/'run.evidence.tar.gz';side=arc.with_name(arc.name+'.sha256')
            r=inspect_archive(arc,side);self.assertEqual(r['cases'][0]['classification'],'CLOCK_DISCONTINUITY_CORRELATED');self.assertEqual(r['internal_verified'],8)
            side.write_text('0'*64+'  '+arc.name+'\n')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA_DRIFT'):inspect_archive(arc,side)
if __name__=='__main__':unittest.main()
