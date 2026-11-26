import hashlib,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_adapters'))
from ch15_adapters.ch13_basic_adapter import authorize,assess
from ch15_adapters.ch14_perception_adapter import adapt
KEYS=['motion_observation','terminal','no_manipulation','worker','goals','engine','children','recording','telemetry','world']
class NativeEdges(unittest.TestCase):
    def test_missing_shared_lock(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);root=p/'native';root.mkdir();(p/'upstream-iit-locomanipulation-d010212').mkdir()
            approval=p/'approval.json';approval.write_text(json.dumps(dict(local_use_approved=True,redistribution=False,upstream_commit='a'*40,review_reference='fixture-only')))
            lock=dict(ch13=dict(upstream=dict(commit='a'*40),assets=[]))
            with patch('ch15_adapters.ch13_basic_adapter.verify_source'),patch('ch15_adapters.ch13_basic_adapter.git',return_value='a'*40),patch('ch15_adapters.ch13_basic_adapter.verify_assets',return_value=94):
                with self.assertRaisesRegex(ValueError,'SHARED_LOCK_MISSING'):authorize(root,lock,dict(base_sha='b'*40),approval)
                (p/'ch13_reuse_engine.lock').touch()
                self.assertEqual(authorize(root,lock,dict(base_sha='b'*40),approval)['asset_count'],94)
    def test_result_scope_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'bag').mkdir();(p/'bag'/'metadata.yaml').write_text('fixture only')
            (p/'source_manifest.json').write_text('{}')
            result=dict(result='PASS',success=True,exercise='basic',scenario='level2_obstacles',scope='basic_navigation_observation_only',full_mission_success=False,bag_closed=True,checks={k:True for k in KEYS},source_manifest_sha256=hashlib.sha256(b'{}').hexdigest())
            def put(name,data):(p/name).write_text(json.dumps(data))
            put('basic_result.json',result);put('bt_summary.json',dict(terminal='SUCCESS',port=dict(requested=['navigate','find','finish'],completed={'navigate':{},'find':{},'finish':{}})));put('navigation_summary.json',dict(result='PASS'))
            after=dict(result='PASS',owned_stack_matches=[],engine_lock_free=True);contract=dict(assessor_keys=KEYS)
            self.assertEqual(assess(p,after,contract,0)['result'],'PASS') # fixture, never actual evidence
            with self.assertRaisesRegex(ValueError,'NATIVE_RUNNER_FAIL'):assess(p,after,contract,1)
            (p/'arm_probe.json').touch()
            with self.assertRaisesRegex(ValueError,'UNEXPECTED_MANIPULATION_ARTIFACT'):assess(p,after,contract,0)
            (p/'arm_probe.json').unlink()
            result['checks']['engine']=False;put('basic_result.json',result)
            with self.assertRaisesRegex(ValueError,'NATIVE_ASSESSOR_NOT_10'):assess(p,after,contract,0)
            result['checks']['engine']=True;put('basic_result.json',result)
            (p/'bag'/'metadata.yaml').unlink()
            with self.assertRaisesRegex(ValueError,'NATIVE_BAG_MISSING'):assess(p,after,contract,0)
    def test_invalid_ch14_metadata(self):
        p=dict(stamp=1,frame='odom',xyz=[1,2,3]);opts=dict(target_class='red_cube',model_sha='a'*64,approved_sha='a'*64,tf_at_source=lambda *a:(1,2,3),ros_ns=2)
        for meta in ({'rgb_stamp':1},{'rgb_stamp':1,'depth_stamp':None,'info_stamp':1,'frame':'opt','depth_frame':'opt','info_frame':'opt','optical_tf':True,'receipt_age':None}):
            result=adapt(p,[],metadata=meta,**opts);self.assertFalse(result['valid']);self.assertTrue(result['reason'].startswith('BLOCKED_COMPATIBILITY'))
if __name__=='__main__':unittest.main()
