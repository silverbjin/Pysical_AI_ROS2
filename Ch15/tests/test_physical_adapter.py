import hashlib,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2_ws/src/ch15_adapters'))
from ch15_adapters.ch13_basic_adapter import verify_assets,verify_source,verify_residual,live_projection,assess,authorize
from ch15_adapters.ch14_perception_adapter import adapt
from ch15_adapters.target_contract import check_metadata,grasp_admissible
class Tests(unittest.TestCase):
    def test_assets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);rows=[]
            for i in range(94):
                path=p/str(i);path.write_bytes(b'a');rows.append(dict(path=str(i),bytes=1,sha256=hashlib.sha256(b'a').hexdigest()))
            self.assertEqual(verify_assets(p,rows),94)
            (p/'0').write_bytes(b'b')
            with self.assertRaisesRegex(ValueError,'ASSET_DRIFT'):verify_assets(p,rows)
            (p/'0').unlink()
            with self.assertRaisesRegex(ValueError,'ASSET_MISSING'):verify_assets(p,rows)
    def test_source(self):
        with patch('ch15_adapters.ch13_basic_adapter.git',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'SOURCE_SHA_DRIFT'):verify_source(Path('/x'),dict(base_sha='expected'))
    def test_lock(self):
        verify_residual(dict(result='PASS',owned_stack_matches=[],engine_lock_free=True))
        with self.assertRaisesRegex(ValueError,'LOCK_BUSY'):verify_residual(dict(result='PASS',owned_stack_matches=[],engine_lock_free=False))
    def test_approval_absent(self):
        with patch('ch15_adapters.ch13_basic_adapter.verify_source'):
            with self.assertRaisesRegex(ValueError,'APPROVAL_MISSING'):authorize(Path('/x'),{}, {},None)
    def test_unexpected_steps(self):
        for name in ('pick','return','place'):
            for key in ('requested','completed'):
                with self.assertRaisesRegex(ValueError,'UNEXPECTED_MANIPULATION'):live_projection({key:[name]})
        self.assertFalse(live_projection(dict(requested=['navigate','find','finish']))['full_mission_success'])
    def test_no_grasp_from_position(self):
        self.assertFalse(grasp_admissible(dict(valid=True,pose_kind='POSITION_ONLY',source='RGBD_COLOR')))
        self.assertFalse(grasp_admissible(dict(valid=True,pose_kind='POSITION_ONLY',source='CH14_ORT')))
    def test_ch14_association(self):
        p=dict(stamp=1000000000,frame='odom',xyz=[1.,0.,0.])
        d=dict(stamp=p['stamp'],frame='camera_optical',confidence=.8,**{'class':'red_cube'})
        meta=dict(rgb_stamp=p['stamp'],depth_stamp=p['stamp'],info_stamp=p['stamp'],frame=d['frame'],depth_frame=d['frame'],info_frame=d['frame'],optical_tf=True,receipt_age=.01)
        opts=dict(target_class='red_cube',model_sha='a'*64,approved_sha='a'*64,tf_at_source=lambda xyz,*args:xyz,ros_ns=p['stamp']+1000000,metadata=meta)
        self.assertEqual(adapt(p,[d],**opts)['pose_kind'],'POSITION_ONLY')
        self.assertFalse(adapt(p,[d,d],**opts)['valid'])
        self.assertFalse(adapt(p,[d],**{**opts,'approved_sha':None})['valid'])
        self.assertFalse(adapt(p,[d],**{**opts,'tf_at_source':None})['valid'])
    def test_metadata(self):
        self.assertEqual(check_metadata(1000000000,1050000000,1000000000,'f','f','f',1100000000,True,.01),'')
        self.assertEqual(check_metadata(1000000000,1051000000,1000000000,'f','f','f',1100000000,True,.01),'SYNC_SKEW')
        self.assertEqual(check_metadata(1000000000,1000000000,1000000000,'f','f','f',1400000000,True,.01),'SOURCE_AGE')
        self.assertEqual(check_metadata(1000000000,1000000000,1000000000,'f','g','f',1100000000,True,.01),'FRAME_OR_TF')
if __name__=='__main__':unittest.main()
