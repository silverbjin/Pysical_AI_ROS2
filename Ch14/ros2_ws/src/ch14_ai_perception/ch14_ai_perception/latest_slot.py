"""Bounded single-worker mailbox: one pending item, one in flight."""
from threading import Condition,Thread
from collections import Counter,deque

class LatestSlot:
    def __init__(self, process):
        self.cv=Condition()
        self.pending=None
        self.results=deque(maxlen=1)
        self.count=Counter()
        self.closed=False
        self.process=process
        self.thread=Thread(target=self._run,name="ch14-inference",daemon=True)
        self.thread.start()

    def put(self,item):
        with self.cv:
            if self.closed: raise RuntimeError("slot closed")
            self.count["received"]+=1
            if self.pending is not None:self.count["overwritten"]+=1
            self.pending=item
            self.cv.notify()

    def invalidate(self):
        with self.cv:
            if self.pending is not None:self.count["invalidated_pending"]+=1
            self.pending=None
            if self.results:self.count["invalidated_result"]+=1
            self.results.clear()

    def _run(self):
        while True:
            with self.cv:
                self.cv.wait_for(lambda:self.closed or self.pending is not None)
                if self.closed:return
                item=self.pending;self.pending=None;self.count["started"]+=1
            try: result=(item,self.process(item),None)
            except Exception as e: result=(item,None,f"{type(e).__name__}: {e}")
            with self.cv:
                self.count["completed"]+=1
                if self.closed:self.count["shutdown_result"]+=1;return
                if self.results:self.count["result_overwritten"]+=1
                self.results.append(result)

    def pop(self):
        with self.cv:return self.results.popleft() if self.results else None

    def snapshot(self):
        with self.cv:return dict(self.count,pending=int(self.pending is not None),
                                 result_pending=len(self.results),worker_alive=self.thread.is_alive())

    def close(self,timeout=10):
        with self.cv:
            self.closed=True
            if self.pending is not None:self.count["invalidated_pending"]+=1
            self.pending=None;self.cv.notify_all()
        self.thread.join(timeout)
        return not self.thread.is_alive()
