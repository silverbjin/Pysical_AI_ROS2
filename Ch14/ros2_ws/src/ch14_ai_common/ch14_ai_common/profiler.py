"""Code 14-13: monotonic stage latency, ROS age and bounded live statistics."""
from collections import deque
import math,time
import numpy as np
from .benchmark import summarize

def interval_ms(a,b):
    if type(a) is not int or type(b) is not int or a<0 or b<a:raise ValueError("invalid monotonic interval")
    return (b-a)/1e6

def ros_age_ms(stamp,now,max_age_ms=300.):
    if type(stamp) is not int or type(now) is not int or stamp<=0 or now<stamp:
        raise ValueError("invalid ROS clock/stamp")
    v=(now-stamp)/1e6
    if not math.isfinite(max_age_ms) or max_age_ms<=0 or v>max_age_ms:raise ValueError("stale result")
    return v

def stage_metrics(receipt,queued,start,pre_end,infer_end,post_end,pub_start,pub_end):
    marks=(receipt,queued,start,pre_end,infer_end,post_end,pub_start,pub_end)
    parts=[interval_ms(a,b) for a,b in zip(marks,marks[1:])]
    return dict(zip(("receive_ms","queue_ms","preprocess_ms","inference_ms","postprocess_ms","result_wait_ms","publish_ms"),parts),
                pipeline_ms=interval_ms(receipt,pub_end))

class PerformanceMonitor:
    def __init__(self,window_size=100,clock=time.monotonic_ns):
        if type(window_size) is not int or window_size<1:raise ValueError("window")
        self.history=deque(maxlen=window_size);self.count=0;self.clock=clock;self.t0=clock()
    def start(self):return self.clock()
    def stop(self,started):
        ms=interval_ms(started,self.clock());self.history.append(ms);return ms
    def published(self):self.count+=1
    def get_stats(self):
        if not self.history:return None
        elapsed=interval_ms(self.t0,self.clock())/1000
        if elapsed<=0:raise ValueError("zero measurement duration")
        return dict(**summarize(self.history),publish_hz=self.count/elapsed)

def count_reconcile(c,s):
    # Only callback/slot boundaries are exact; DDS pre-callback loss needs source stamps.
    started=s.get("started",c.get("sync_started",0))
    completed=s.get("completed",started)
    accepted=c.get("accepted",0)
    overwritten=s.get("overwritten",0)
    invalid_pending=s.get("invalidated_pending",0)
    pending=s.get("pending",0)
    return dict(accepted=accepted,started=started,completed=completed,overwritten=overwritten,
                invalidated_pending=invalid_pending,pending=pending,published=c.get("published",0),
                accepted_residual=accepted-started-overwritten-invalid_pending-pending,
                in_flight=started-completed,completed_not_published=completed-c.get("published",0))

def real_time_factor(first_ros,last_ros,first_wall,last_wall):
    if first_ros<0 or last_ros<first_ros:raise ValueError("ROS clock reset")
    elapsed=interval_ms(first_wall,last_wall)
    if elapsed<=0:raise ValueError("zero wall interval")
    return (last_ros-first_ros)/1e6/elapsed
