from types import SimpleNamespace
import numpy as np
import pytest
import ch13_navigation_reuse.sensors as sensors


def test_capture_profile_separates_pre_offer_work_without_replacing_source_time(monkeypatch,tmp_path):
    clock=[10.];offered=[]
    monkeypatch.setattr(sensors,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    def scan(*args):clock[0]+=.07;return [1.]*181
    def publish_state(*args):clock[0]+=.08
    def offer(q,stamp,source_wall):
        offered.append((q.copy(),stamp,source_wall));clock[0]+=.01;return True
    monkeypatch.setattr(sensors,'ray_scan',scan)
    suite=sensors.SensorSuite(None,None,'free',tmp_path,latest_camera=True)
    suite.camera=SimpleNamespace(offer=offer);suite.node=SimpleNamespace(publish_state=publish_state)
    suite.scan_pub=SimpleNamespace(publish=lambda msg:None)
    state=dict(stamp_ns=1234);q=np.array([1.,2.]);platform=SimpleNamespace(mjModel=None,mjData=SimpleNamespace(qpos=q))
    suite.step(platform,state)
    row=suite.capture_stage_timing[-1]
    assert row['capture_ns']==1234 and row['capture_wall']==10.
    assert row['scan_wall_s']==pytest.approx(.07)
    assert row['state_publish_wall_s']==pytest.approx(.08)
    assert row['request_offer_wall_s']==pytest.approx(.01)
    assert row['pre_offer_wall_s']==pytest.approx(.15)
    assert offered[0][1:]==(1234,10.)
    np.testing.assert_array_equal(offered[0][0],q)
