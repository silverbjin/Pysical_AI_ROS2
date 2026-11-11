"""Submit the immutable capture before slow owner-side TF serialization."""
from collections import deque
from types import SimpleNamespace
import numpy as np,pytest
from ch13_navigation_reuse.sensors import SensorSuite
import ch13_navigation_reuse.sensors as sensors

@pytest.mark.parametrize('overlap',[False,True])
def test_capture_overlap_preserves_snapshot_and_original_stamp(overlap):
    suite=SensorSuite.__new__(SensorSuite);suite.overlap_capture=overlap
    suite.next_scan=float('inf');suite.next_rgb=0.;suite.camera=object()
    suite.latest_camera=True;suite.capture_stage_total=0;suite.capture_stage_timing=deque(maxlen=256)
    events=[];p=SimpleNamespace(mjData=SimpleNamespace(qpos=np.array([1.,2.,3.])))
    state={'stamp_ns':1234567};submitted=[]
    def offer(q,stamp,wall):
        events.append('capture');submitted.append((q.copy(),stamp,wall));return True
    def publish(robot,snapshot):
        assert snapshot is state;events.append('state');robot.mjData.qpos[0]=99.
    suite.request_capture=offer;suite.node=SimpleNamespace(publish_state=publish)
    suite.step(p,state)
    assert events==(['capture','state'] if overlap else ['state','capture'])
    assert submitted[0][1]==state['stamp_ns']
    np.testing.assert_array_equal(submitted[0][0],[1.,2.,3.])
    assert submitted[0][2]==suite.capture_stage_timing[-1]['capture_wall']


@pytest.mark.parametrize('enabled',[None,'0','1'])
def test_overlap_is_experimental_opt_in_after_actual_survey_regression(monkeypatch,enabled):
    monkeypatch.setenv('CH13_VALIDATION_PROFILE','carry_v1')
    if enabled is None:monkeypatch.delenv('CH13_CAPTURE_OVERLAP',raising=False)
    else:monkeypatch.setenv('CH13_CAPTURE_OVERLAP',enabled)
    monkeypatch.setattr(sensors,'CameraWorker',lambda *args,**kwargs:object())
    model=SimpleNamespace(camera=lambda name:SimpleNamespace(id=0),cam_pos=np.array([[.4,.4,.29]]),
                          cam_quat=np.array([[1.,0.,0.,0.]]))
    suite=SensorSuite(model,SimpleNamespace(qpos=np.zeros(34)),'vision','unused',latest_camera=True)
    assert suite.overlap_capture is (enabled=='1')


def test_overlap_submits_original_snapshot_before_measured_scan_delay(monkeypatch,tmp_path):
    clock=[10.];submitted=[];events=[]
    monkeypatch.setattr(sensors,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    def scan(*args):events.append('scan');clock[0]+=.042;return [1.]*181
    monkeypatch.setattr(sensors,'ray_scan',scan)
    suite=SensorSuite(None,None,'free',tmp_path,latest_camera=True);suite.overlap_capture=True
    def offer(q,stamp,source_wall):
        events.append('capture');submitted.append((q,stamp,source_wall,clock[0]));return True
    def publish(*args):events.append('state');clock[0]+=.088
    suite.camera=SimpleNamespace(offer=offer);suite.node=SimpleNamespace(publish_state=publish)
    suite.scan_pub=SimpleNamespace(publish=lambda msg:None)
    q=np.array([1.,2.]);platform=SimpleNamespace(mjModel=None,mjData=SimpleNamespace(qpos=q))
    suite.step(platform,dict(stamp_ns=1234));q[0]=99.
    assert events==['capture','scan','state']
    assert submitted[0][1:]==(1234,10.,10.)
    np.testing.assert_array_equal(submitted[0][0],[1.,2.])
    row=suite.capture_stage_timing[-1]
    assert row['capture_wall']==10. and row['pre_offer_wall_s']==0.
    assert row['scan_wall_s']==pytest.approx(.042)
    assert row['state_publish_wall_s']==pytest.approx(.088)
