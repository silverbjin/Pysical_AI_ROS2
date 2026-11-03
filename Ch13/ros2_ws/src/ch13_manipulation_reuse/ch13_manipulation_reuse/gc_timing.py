"""Observe process-local cyclic collection without changing GC policy."""
import gc
import threading
import time


class GCTiming:
    def __init__(self,minimum_s=.005):
        self.minimum_s=minimum_s;self.events=[];self.counts={};self.pending={};self.running=False

    def callback(self,phase,info):
        key=(threading.get_ident(),info['generation'])
        if phase=='start':self.pending[key]=(time.monotonic(),time.thread_time())
        elif phase=='stop':
            start=self.pending.pop(key,None)
            if start is None:return
            end=time.monotonic();cpu=time.thread_time()-start[1]
            self.counts[info['generation']]=self.counts.get(info['generation'],0)+1
            if end-start[0]>=self.minimum_s:
                self.events.append(dict(generation=info['generation'],thread_id=key[0],start_wall=start[0],end_wall=end,
                                        wall_s=end-start[0],thread_cpu_s=cpu,collected=info.get('collected'),
                                        uncollectable=info.get('uncollectable')))

    def start(self):
        if not self.running:gc.callbacks.append(self.callback);self.running=True

    def stop(self):
        if self.running:gc.callbacks.remove(self.callback);self.running=False

    def summary(self):return dict(policy_changed=False,counts=self.counts,events=self.events)
