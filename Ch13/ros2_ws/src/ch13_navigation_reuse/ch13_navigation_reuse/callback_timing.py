"""Opt-in bounded monotonic callback spans; never alters message authority."""
from collections import deque
from functools import wraps
import threading
import time


class CallbackTiming:
    def __init__(self, limit=4096):
        self.rows=deque(maxlen=limit);self.total=0

    def record(self, name, start, cpu, raised):
        end=time.monotonic();elapsed_cpu=time.thread_time()-cpu
        self.rows.append(dict(name=name,start_wall=start,end_wall=end,
                              cpu_s=elapsed_cpu,thread_id=threading.get_native_id(),raised=raised))
        self.total+=1

    def summary(self):
        return dict(scope='diagnostic monotonic callback spans; no scheduling or timestamp changes',
                    limit=self.rows.maxlen,total=self.total,rows=list(self.rows))


def timed_callback(name, channel_index=None):
    def decorate(callback):
        @wraps(callback)
        def invoke(self, *args, **kwargs):
            owner=getattr(self,'node',self)
            trace=getattr(owner,'callback_timing',None)
            if trace is None:return callback(self,*args,**kwargs)
            label=name if channel_index is None else name+':'+str(args[channel_index])
            start=time.monotonic();cpu=time.thread_time();raised=True
            try:
                result=callback(self,*args,**kwargs);raised=False;return result
            finally:trace.record(label,start,cpu,raised)
        return invoke
    return decorate
