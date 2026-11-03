import gc
from ch13_manipulation_reuse.gc_timing import GCTiming


def test_gc_probe_records_actual_collection_and_restores_its_callback():
    before=list(gc.callbacks);enabled=gc.isenabled()
    probe=GCTiming(minimum_s=0.)
    try:
        probe.start();gc.collect(2)
        event=probe.summary()['events'][-1]
        assert event['generation']==2 and event['wall_s']>=0 and event['thread_cpu_s']>=0
        assert event['end_wall']>=event['start_wall']
        assert gc.isenabled()==enabled
    finally:probe.stop()
    assert list(gc.callbacks)==before and gc.isenabled()==enabled
