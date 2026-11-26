import numpy as np
from ch14_ai_common.backend_comparison import matched_gt,parity
from ch14_ai_common.yolo import Detection,preprocess

def test_one_to_one_gt():
    labels=[dict(class_id=0,xyxy=[0,0,10,10]),dict(class_id=0,xyxy=[30,30,40,40])]
    d=Detection(0,.9,(0,0,10,10))
    assert matched_gt([d,d],labels)=={0}

def test_equal_counts_different_gt_not_equal():
    labels=[dict(class_id=0,xyxy=[0,0,10,10]),dict(class_id=0,xyxy=[30,30,40,40])]
    a=Detection(0,.9,(0,0,10,10));b=Detection(0,.9,(30,30,40,40))
    assert matched_gt([a],labels)!=matched_gt([b],labels)

def test_baseline_miss_not_new_miss():
    _,meta=preprocess(np.zeros((640,640,3),np.uint8))
    a=np.zeros((1,84,8400),np.float32)
    row=dict(id=1,all_labels=[dict(class_id=0,xyxy=[0,0,10,10])],targets=[dict(class_id=0,xyxy=[0,0,10,10])])
    r=parity(a,a.copy(),meta,row)
    assert r["status"]=="PASS" and r["absolute_required_count"]==1 and not r["candidate_required_hits"]
