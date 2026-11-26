import pathlib,sys,unittest
import numpy as np,cv2
root=pathlib.Path(__file__).resolve().parents[1]/'ros2_ws/src'
sys.path[:0]=[str(root/'ch15_simulation'),str(root/'ch15_adapters')]
from ch15_simulation.cube_detector import locate,rotation
from ch15_adapters.target_contract import check_metadata
class Tests(unittest.TestCase):
    def setUp(self):
        self.rgb=np.zeros((100,100,3),np.uint8);self.rgb[40:60,40:60]=[0,0,255]
        self.depth=np.ones((100,100),np.float32);self.k=[100.,0.,49.5,0.,100.,49.5,0.,0.,1.]
    def test_cube(self):
        r,e=locate(self.rgb,self.depth,self.k);self.assertEqual(e,'');self.assertEqual(r['bbox'],[40,40,60,60]);np.testing.assert_allclose(r['optical'],[0,0,1.025])
    def test_invalid_depth(self):
        self.depth[:]=np.nan;self.assertEqual(locate(self.rgb,self.depth,self.k)[1],'INVALID_DEPTH')
    def test_occluded(self):
        self.rgb[:]=0;self.assertEqual(locate(self.rgb,self.depth,self.k)[1],'NO_UNIQUE_RED_COMPONENT')
    def test_two_objects(self):
        self.rgb[10:20,10:20]=[0,0,255];self.assertEqual(locate(self.rgb,self.depth,self.k)[1],'NO_UNIQUE_RED_COMPONENT')
    def test_tf_and_stamp(self):
        self.assertEqual(check_metadata(1,1,1,'opt','opt','opt',1,False,0.),'FRAME_OR_TF')
        self.assertEqual(check_metadata(1,1,1,'opt','opt','opt',300000002,True,0.),'SOURCE_AGE')
        with self.assertRaises(ValueError):rotation([0,0,0,0])
if __name__=='__main__':unittest.main()
