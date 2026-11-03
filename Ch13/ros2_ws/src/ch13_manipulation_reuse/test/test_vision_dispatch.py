import json
from types import SimpleNamespace
import pytest
from ch13_navigation_reuse.vision_approach import VisionObserver
from ch13_navigation_reuse.vision_geometry import FrameCache


@pytest.mark.parametrize('latest,expected',[(True,1),(False,0)])
def test_complete_original_frame_can_dispatch_without_next_timer(latest,expected):
    observer=VisionObserver.__new__(VisionObserver)
    observer.latest_camera=latest;observer.cache=FrameCache();observer.receipt_rows=[]
    calls=[];observer.tick=lambda:calls.append(True)
    info=dict(receipt_wall=10.,publisher_gid=b'camera',native_receipt_wall=10.,canonical_sha256='x',
              canonical_bytes=1,relay_gid='relay',source_timestamp=1)
    header=SimpleNamespace(frame_id='reuse/camera_optical',stamp=SimpleNamespace(sec=1,nanosec=0))
    message=SimpleNamespace(header=header,width=320,height=240)
    for key in ('rgb','depth','camera_info'):
        observer.camera_frame(key,message,info)
        assert not calls,'partial frames must not dispatch'
    observer.camera_frame('camera_meta',SimpleNamespace(data=json.dumps({'capture_ns':1_000_000_000})),info)
    assert len(calls)==expected
