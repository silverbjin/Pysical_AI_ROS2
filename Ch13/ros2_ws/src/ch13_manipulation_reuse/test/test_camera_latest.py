import queue
import threading
from ch13_navigation_reuse.camera_worker import put_render_result


def test_latest_output_drops_waiting_frame_without_restamping_new_frame():
    results=queue.Queue(maxsize=1);stop=threading.Event()
    old=('rgb1','depth1',{'capture_ns':1,'capture_wall':10.})
    new=('rgb2','depth2',{'capture_ns':2,'capture_wall':10.07})
    results.put(old)
    dropped=put_render_result(results,new,stop,latest=True)
    assert dropped==1
    assert results.get_nowait() is new
    assert new[2]=={'capture_ns':2,'capture_wall':10.07}
