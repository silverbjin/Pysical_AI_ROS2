import pytest
from ch14_ai_common.profiler import PerformanceMonitor,stage_metrics,ros_age_ms,interval_ms,real_time_factor,count_reconcile

def test_fake_clock_and_publish_only():
    ticks=iter([0,1_000_000,4_000_000,5_000_000,10_000_000,20_000_000])
    m=PerformanceMonitor(clock=lambda:next(ticks))
    assert m.get_stats() is None
    assert m.stop(m.start())==3
    assert m.stop(m.start())==5
    m.published()
    a=m.get_stats()
    assert a["mean_ms"]==4 and a["p95_ms"]==4.9 and a["publish_hz"]==50

def test_stages_add_up():
    d=stage_metrics(*[i*1_000_000 for i in range(8)])
    assert d["pipeline_ms"]==7 and sum(v for k,v in d.items() if k!="pipeline_ms")==7

@pytest.mark.parametrize("a,b",[(2,1),(-1,1),(float("nan"),1),(1,float("inf"))])
def test_bad_clock(a,b):
    with pytest.raises(ValueError):interval_ms(a,b)

def test_age_and_rtf():
    assert ros_age_ms(1,300000001)==300
    for a,b in [(0,1),(2,1),(1,300000002)]:
        with pytest.raises(ValueError):ros_age_ms(a,b)
    assert real_time_factor(1000000000,1500000000,0,1000000000)==.5
    with pytest.raises(ValueError):real_time_factor(2,1,0,1)

def test_count_residual():
    assert count_reconcile({"accepted":6,"published":2},{"started":3,"completed":3,"overwritten":2,"invalidated_pending":1})["accepted_residual"]==0
    assert count_reconcile({"accepted":2,"sync_started":2,"published":1},{})["completed_not_published"]==1
