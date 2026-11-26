import numpy as np
import pytest
from ch14_ai_common.backends import check_tensor, SHAPE_IN, NAMES, entry_for
from ch14_ai_common.yolo import Detection
from ch14_ai_common.yolo_lab import match, targets_ok

def test_input_contract():
    assert len(NAMES)==80
    x=np.zeros(SHAPE_IN,np.float32)
    assert check_tensor(x,SHAPE_IN) is x
    for bad in (x.astype(np.float64),x[:,:,:5],np.full(SHAPE_IN,np.nan,np.float32)):
        with pytest.raises(ValueError):check_tensor(bad,SHAPE_IN)
def test_match_one_to_one():
    a=Detection(1,.9,(1.,2.,50.,60.))
    b=Detection(1,.89,(1.,2.,50.,60.))
    result=match([a,a],[b])
    assert len(result["pairs"])==1 and len(result["unmatched_reference"])==1
    assert not match([a],[Detection(2,.9,a.xyxy)])["pairs"]
    assert not match([a],[Detection(1,.7,a.xyxy)])["pairs"]
def test_gt_required():
    a=Detection(1,.9,(1.,2.,50.,60.))
    assert targets_ok([a],[{"class_id":1,"xyxy":a.xyxy}])
    assert not targets_ok([a],[{"class_id":2,"xyxy":a.xyxy}])
def test_manifest_rejected():
    with pytest.raises(ValueError):entry_for({"models":[]},"yolov8n")
