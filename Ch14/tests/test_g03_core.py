import threading,time
import numpy as np
import pytest
from ch14_ai_perception.latest_slot import LatestSlot
from ch14_ai_perception.freshness import Freshness
from ch14_ai_perception.depth_geometry.geometry import decode_depth,sample_depth,deproject
from ch14_ai_perception.depth_geometry.contracts import Box2D,Intrinsics

def test_latest_slot_1_4():
    entered=threading.Event();release=threading.Event();processed=[]
    def process(i):
        processed.append(i)
        if i==1:entered.set();assert release.wait(2)
        return i
    s=LatestSlot(process)
    try:
        s.put(1);assert entered.wait(2)
        for i in [2,3,4]:s.put(i)
        release.set()
        until=time.monotonic()+2
        while s.snapshot().get("completed",0)<2 and time.monotonic()<until:time.sleep(.01)
        assert processed==[1,4]
        assert s.snapshot()["overwritten"]==2
        assert s.snapshot()["pending"]==0
    finally:release.set();assert s.close()

def test_freshness_and_clock():
    g=Freshness(True)
    assert g.accept(1_000_000_000,1_000_000_000,0) is None
    assert g.accept(1_000_000_000,1_000_000_001,1)=="OUT_OF_ORDER"
    assert g.check(1_000_000_001,1_000_000_000,2,g.epoch)=="EPOCH_INVALID"
    ep=g.epoch
    assert g.check(1,1_000_000_000,3,ep)=="STALE"
    assert g.check(1_000_000_001,1_000_000_000,4,ep)=="FUTURE"
    assert g.check(1_000_000_000,1_000_000_000,500_000_004,ep)=="CLOCK_PAUSED"

def test_depth_si_and_invalid():
    a=np.full((10,10),2000,dtype=">u2")
    d=decode_depth(a.tobytes(),"16UC1",10,10,20,True)
    b=Box2D(5,5,6,6,"bus",.9)
    z,mad=sample_depth(d,b)
    assert (z,mad)==(2.,0.)
    np.testing.assert_allclose(deproject(5,5,z,Intrinsics(10,10,10.,10.,5.,5.,"camera","id")),[0,0,2])
    with pytest.raises(ValueError):sample_depth(np.zeros((10,10)),b)
    with pytest.raises(ValueError):decode_depth(b"1","32FC1",10,10,40,False)

def test_ats_exact_boundary():
    from message_filters import SimpleFilter,ApproximateTimeSynchronizer
    from sensor_msgs.msg import Image
    from builtin_interfaces.msg import Time
    for delta,expected in [(49_000_000,1),(50_000_000,1),(51_000_000,0)]:
        filters=[SimpleFilter() for _ in range(3)]
        ats=ApproximateTimeSynchronizer(filters,10,.050000001)
        result=[];ats.registerCallback(lambda *xs:result.append(xs))
        for f,n in zip(filters,[1_000_000_000,1_000_000_000-delta,1_000_000_000]):
            m=Image();m.header.stamp=Time(sec=n//1_000_000_000,nanosec=n%1_000_000_000)
            f.signalMessage(m)
        assert len(result)==expected
