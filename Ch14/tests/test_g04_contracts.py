from dataclasses import FrozenInstanceError
from pathlib import Path
import threading,time
import pytest
from ch14_ai_perception.parameters import DEFAULTS,validate_startup,validate_update,snapshot
from ch14_ai_perception.model_slot import Active,Entry,ModelSlot

def startup():
    return dict(DEFAULTS,model_path="/tmp/n.onnx",model_sha256="a"*64)

def test_defaults_and_boundaries():
    p=validate_startup(startup());assert snapshot(p).confidence==.5 and snapshot(p).iou==.45
    for v in (0.,1.):validate_update([("confidence_threshold",v),("iou_threshold",v)])
    with pytest.raises(FrozenInstanceError):snapshot(p).confidence=.1

@pytest.mark.parametrize("v",[-.01,1.01,float("nan"),float("inf"),1,True,"0.5",None])
def test_bad_values(v):
    with pytest.raises(ValueError):validate_update([("confidence_threshold",v)])
    with pytest.raises(ValueError):validate_startup(dict(startup(),confidence_threshold=v))

def test_atomic_validation_and_startup_only():
    for name in ("model_path","onnx","backend","use_sim_time","max_age_sec","input_topic","threads","unknown"):
        with pytest.raises(ValueError):validate_update([("confidence_threshold",.7),(name,.5)])
    with pytest.raises(ValueError):validate_update([("confidence_threshold",.7),("confidence_threshold",.8)])
    with pytest.raises(ValueError):validate_startup(dict(startup(),onnx="/tmp/other.onnx"))
    with pytest.raises(ValueError):validate_startup(dict(startup(),max_age_sec=.31))

def test_worker_boundary_and_rollback():
    old=object();new=object();gate=threading.Event();entered=threading.Event();events=[]
    entries={i:Entry(i,Path("/tmp/"+i),h*64,Path("/tmp/ref"),"c"*64) for i,h in [("yolov8n","a"),("yolov8s","b")]}
    def load(e):
        entered.set();assert gate.wait(2)
        if e.model_id=="yolov8n":raise ValueError("corrupt")
        return new,{"max_abs":0.}
    s=ModelSlot(Active("yolov8n","a"*64,old),entries,load,events.append)
    def poll():
        end=time.monotonic()+2
        while s.state=="LOADING" and time.monotonic()<end:s.poll();time.sleep(.001)
    try:
        ok,rid,_=s.request("yolov8s");assert ok and entered.wait(1)
        assert s.request("yolov8s")[2]=="BUSY"
        assert s.active.engine is old and s.active.generation==0
        gate.set();poll();assert s.state=="DRAINING" and s.active.engine is old
        assert s.commit().engine is old and s.active.engine is new and s.active.generation==1
        assert events[-1]["request_id"]==rid and events[-1]["state"]=="SUCCEEDED"
        ok,rid,_=s.request("yolov8n");assert ok;poll()
        assert s.state=="IDLE" and s.active.engine is new and s.active.generation==1
        assert events[-1]["request_id"]==rid and events[-1]["state"]=="FAILED"
        assert s.request("../bad")[2]=="UNAPPROVED_MODEL"
    finally:gate.set();assert s.close()
