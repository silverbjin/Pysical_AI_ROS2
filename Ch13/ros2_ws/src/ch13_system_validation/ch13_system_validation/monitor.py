"""Clock-separated topic metrics and CPU for this process and descendants."""
import math
import os
import time
from pathlib import Path
from statistics import mean


class TopicStats:
    def __init__(self):
        self.receipts=[];self.delays=[];self.ages=[];self.last_stamp=None
        self.reordered=0;self.missing=0

    def add(self,stamp_ns,receipt_wall,*,clock_ns=None,capture_wall=None):
        self.receipts.append(receipt_wall)
        if stamp_ns is None:self.missing+=1
        else:
            if self.last_stamp is not None and stamp_ns<self.last_stamp:self.reordered+=1
            self.last_stamp=stamp_ns
            if clock_ns is not None:self.delays.append((clock_ns-stamp_ns)/1e9)
        if capture_wall is not None:self.ages.append(receipt_wall-capture_wall)

    def report(self):
        span=self.receipts[-1]-self.receipts[0] if len(self.receipts)>1 else 0.
        return dict(count=len(self.receipts),receipt_hz=(len(self.receipts)-1)/span if span>0 else None,
                    mean_sim_delay_s=mean(self.delays) if self.delays else None,
                    max_capture_age_wall_s=max(self.ages) if self.ages else None,
                    reordered=self.reordered,missing_stamps=self.missing)


def cpu_percent(cpu_seconds,wall_seconds,allowed_cores):
    if not all(math.isfinite(v) for v in (cpu_seconds,wall_seconds,allowed_cores)) or cpu_seconds<0 or wall_seconds<=0 or allowed_cores<=0:
        raise ValueError('positive CPU denominator and finite counters required')
    return 100.*cpu_seconds/wall_seconds/allowed_cores


class ProcessCPU:
    def __init__(self):
        self.previous={};self.last_wall=None;self.rows=[]
        self.cores=len(os.sched_getaffinity(0));self.hz=os.sysconf('SC_CLK_TCK')

    def sample(self):
        now=time.monotonic()
        if self.last_wall is not None and now-self.last_wall<1.:return
        table={}
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                fields=path.read_text().rsplit(') ',1)[1].split()
                table[int(path.parent.name)]=(int(fields[1]),int(fields[19]),(int(fields[11])+int(fields[12]))/self.hz)
            except (FileNotFoundError,PermissionError,ProcessLookupError,ValueError,IndexError):continue
        owned={os.getpid()}
        while True:
            added={pid for pid,(parent,_,_) in table.items() if parent in owned}-owned
            if not added:break
            owned.update(added)
        current={(pid,table[pid][1]):table[pid][2] for pid in owned if pid in table}
        if self.last_wall is not None:
            seconds=sum(max(0.,value-self.previous.get(key,value)) for key,value in current.items())
            self.rows.append(dict(wall=now,percent=cpu_percent(seconds,now-self.last_wall,self.cores),owned_pids=sorted(owned)))
        self.previous=current;self.last_wall=now
