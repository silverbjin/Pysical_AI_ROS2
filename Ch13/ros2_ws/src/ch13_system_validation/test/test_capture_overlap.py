"""Submit the immutable capture before slow owner-side TF serialization."""
from collections import deque
from types import SimpleNamespace
import numpy as np,pytest
from ch13_navigation_reuse.sensors import SensorSuite

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
