"""Opt-in bounded metadata trace; never changes source stamps or gate policy."""
from collections import deque
import json,os
from pathlib import Path


def require_startup_service(name):
    if name not in ('navigation/idle','platform/shutdown'):
        raise ValueError('startup-only diagnostic forbids motion admission: '+name)


class StartupTrace:
    def __init__(self,directory,name,capacity=2048):
        self.path=Path(directory)/(name+'_startup_trace.json');self.events=deque(maxlen=capacity)
        self.total=0;self.first_fault=None;self.name=name;self.pid=os.getpid()
        self.boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    @classmethod
    def from_env(cls,name):
        directory=os.environ.get('CH13_REUSE_STARTUP_TRACE')
        return cls(directory,name) if directory else None

    def add(self,**row):
        if self.first_fault is None:self.total+=1;self.events.append(row)

    def packet(self,key,stamp,info,now,clock_ns,clock_receipt):
        self.add(event='packet',key=key,stamp_ns=stamp,native_receipt_wall=info['receipt_wall'],
                 process_wall=now,publisher_gid=info['publisher_gid'].hex(),relay_gid=info['relay_gid'],
                 clock_ns=clock_ns,clock_receipt_wall=clock_receipt)

    def inbox(self,event,key,stamp,receipt,clock_ns,now,clock_receipt):
        self.add(event=event,key=key,stamp_ns=stamp,native_receipt_wall=receipt,process_wall=now,
                 clock_ns=clock_ns,clock_receipt_wall=clock_receipt)

    def fault(self,reason,pending,clock_ns,clock_receipt,now):
        if self.first_fault is not None:return
        rows=[]
        for key,(stamp,receipt,payload) in pending.items():
            info=payload[2]
            rows.append(dict(key=key,stamp_ns=stamp,receipt_wall=receipt,
                             publisher_gid=info['publisher_gid'].hex(),relay_gid=info['relay_gid']))
        self.first_fault=dict(reason=reason,pending=rows,clock_ns=clock_ns,
                              clock_receipt_wall=clock_receipt,decision_wall=now)

    def write(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(dict(name=self.name,pid=self.pid,boot_id=self.boot_id,
            clock_domain='wall fields: CLOCK_MONOTONIC within this boot; stamp fields: simulation ns',
            fault=self.first_fault,events=list(self.events),discarded_events=self.total-len(self.events)),indent=2)+'\n')
