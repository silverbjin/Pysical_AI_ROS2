"""One owned writer for advisory latest status, outside the ROS executor."""
import copy
import json
from pathlib import Path
import threading


class LiveStatusWriter:
    def __init__(self,path,*,emit=None):
        self.path=Path(path);self.emit=emit or self._write
        self.condition=threading.Condition();self.pending=None;self.stopping=False
        self.published=0;self.write_errors=0;self.overwritten=0;self.last_error=None
        self.thread=threading.Thread(target=self._run,name='ch13_advisory_status_writer',daemon=False)
        self.thread.start()

    def offer(self,snapshot):
        value=copy.deepcopy(snapshot)
        with self.condition:
            if self.stopping:raise RuntimeError('advisory writer already closing')
            if self.pending is not None:self.overwritten+=1
            self.pending=value;self.condition.notify()

    def _write(self,value):
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
        temporary.replace(self.path)

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:self.pending is not None or self.stopping)
                if self.pending is None:return
                value=self.pending;self.pending=None
            try:self.emit(value)
            except (OSError,ValueError,TypeError) as error:
                with self.condition:
                    self.write_errors+=1;self.last_error=type(error).__name__+': '+str(error)
            else:
                with self.condition:self.published+=1

    def close(self,timeout=5.):
        with self.condition:self.stopping=True;self.condition.notify()
        self.thread.join(timeout)
        with self.condition:
            return dict(scope='advisory status delivery only; never live authority or final verdict',
                joined=not self.thread.is_alive(),published=self.published,write_errors=self.write_errors,
                overwritten_waiting=self.overwritten,last_error=self.last_error)
