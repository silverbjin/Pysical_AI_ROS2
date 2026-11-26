import unittest
from g01_check_reuse import check_fresh

BASE=dict(model="yolov8n",status="PASS",source_sha256="a"*64,onnx_sha256="b"*64,class_map_sha256="c"*64,
          input_shape=[1,3,640,640],output_shape=[1,84,8400],dtype="float32",opset=13,nms=False,
          provider="CPUExecutionProvider",classes=["fixture"],seed_max_abs=.001)
class FreshTests(unittest.TestCase):
    def test_new_bytes_are_fresh_not_reuse(self):
        fresh=dict(BASE,onnx_sha256="d"*64)
        self.assertEqual(check_fresh(BASE,fresh,"d"*64)["mode"],"FRESH_T02_VALIDATED_NOT_REUSED")
    def test_same_bytes(self):
        self.assertEqual(check_fresh(BASE,BASE,"b"*64)["mode"],"SAME_BYTES_VERIFIED")
    def test_wrong_contract_rejected(self):
        for fresh,actual in [(dict(BASE,status="FAIL"),"b"*64),(dict(BASE,opset=17),"b"*64),(BASE,"d"*64),(dict(BASE,seed_max_abs=float("nan")),"b"*64)]:
            with self.assertRaises(ValueError):check_fresh(BASE,fresh,actual)
if __name__=="__main__":unittest.main(verbosity=2)
