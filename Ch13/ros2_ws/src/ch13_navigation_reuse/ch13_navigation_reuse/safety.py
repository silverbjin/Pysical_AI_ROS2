"""ROS-independent single-owner, source-time-preserving command safety gate."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Decision:
    vx: float
    wz: float
    stamp_ns: int
    mode: str
    fault: str

class Guard:
    timeout_s=.30
    age_ns=300_000_000
    future_ns=25_000_000
    def __init__(self, required=('raw','base','joints'), control='raw'):
        self.required=tuple(required);self.control=control
        self.reset()
    def reset(self):
        self.samples={};self.owners={};self.mode='DISARMED';self.fault='';self.fault_details=None
        self.clock_ns=0;self.clock_wall=None;self.counts={};self.graph_wall=None
        self.values=(0.,0.);self.last_values=(0.,0.);self.last_output_wall=None;self.last_output_clock_ns=None
    def trip(self, reason):
        if self.mode!='FAULT':self.fault=reason
        self.mode='FAULT';self.last_values=(0.,0.)
    def _owner(self, topic, gid):
        if not gid:self.trip('NO_GID:'+topic);return False
        if topic in self.owners and self.owners[topic]!=gid:self.trip('OWNER_REPLACED:'+topic);return False
        self.owners.setdefault(topic,gid);return True
    def clock(self, ns, wall, gid='clock'):
        if not isinstance(ns,int) or ns<0 or not math.isfinite(wall):self.trip('INVALID_CLOCK');return
        if not self._owner('clock',gid):return
        if self.clock_wall is not None:
            if ns<self.clock_ns:self.trip('CLOCK_ROLLBACK');return
            if ns==self.clock_ns:return
        self.clock_ns=ns;self.clock_wall=wall
    def graph(self, counts, wall):
        self.counts=dict(counts);self.graph_wall=wall
        for topic,count in counts.items():
            if count>1:self.trip('DUPLICATE_OWNER:'+topic)
    def observe(self, topic, stamp, wall, gid, valid=True):
        if self.mode=='FAULT':return False
        if not valid:self.trip('INVALID_STATE:'+topic);return False
        if not isinstance(stamp,int) or stamp<=0 or not math.isfinite(wall):self.trip('INVALID_STAMP:'+topic);return False
        if not self._owner(topic,gid):return False
        if self.clock_wall is None:return False
        if stamp>self.clock_ns+self.future_ns:self.trip('FUTURE_SOURCE:'+topic);return False
        if self.clock_ns-stamp>self.age_ns:self.trip('OLD_SOURCE:'+topic);return False
        previous=self.samples.get(topic)
        if previous:
            if stamp<previous[0]:self.trip('SOURCE_REORDER:'+topic);return False
            if stamp==previous[0]:return False
        self.samples[topic]=(stamp,wall,gid)
        return True
    def command(self, stamp, wall, gid, values, frame='reuse/nav_base'):
        if (frame!='reuse/nav_base' or len(values)!=6
                or not all(math.isfinite(x) for x in values)
                or any(abs(values[i])>1e-12 for i in [1,2,3,4])):
            self.trip('INVALID_COMMAND');return False
        if not self.observe(self.control,stamp,wall,gid):return False
        self.values=(max(-.2,min(.2,float(values[0]))),max(-.2,min(.2,float(values[5]))))
        return True
    def _fresh(self, wall):
        if self.clock_wall is None or wall-self.clock_wall>self.timeout_s:return False
        if self.graph_wall is None or wall-self.graph_wall>self.timeout_s:return False
        if any(self.counts.get(topic,0)!=1 for topic in ('clock',)+self.required):return False
        for topic in self.required:
            sample=self.samples.get(topic)
            if sample is None or wall-sample[1]>self.timeout_s or self.clock_ns-sample[0]>self.age_ns:return False
        if 'base' in self.samples and 'joints' in self.samples:
            if abs(self.samples['base'][0]-self.samples['joints'][0])>40_000_000:return False
        return True
    def arm(self, wall):
        if self.mode!='DISARMED' or not self._fresh(wall) or any(abs(x)>1e-12 for x in self.values):return False
        self.mode='ARMED';self.last_output_wall=wall;self.last_output_clock_ns=self.clock_ns;self.last_values=(0.,0.);return True
    def freshness_details(self, wall):
        """Snapshot the first failed predicate; never refresh source receipts."""
        failed=[]
        if self.clock_wall is None:failed.append('clock_missing')
        elif wall-self.clock_wall>self.timeout_s:failed.append('clock_wall_expired')
        if self.graph_wall is None:failed.append('graph_missing')
        elif wall-self.graph_wall>self.timeout_s:failed.append('graph_wall_expired')
        for topic in ('clock',)+self.required:
            if self.counts.get(topic,0)!=1:failed.append('owner_count:'+topic)
        for topic in self.required:
            sample=self.samples.get(topic)
            if sample is None:failed.append('sample_missing:'+topic);continue
            if wall-sample[1]>self.timeout_s:failed.append('sample_wall_expired:'+topic)
            if self.clock_ns-sample[0]>self.age_ns:failed.append('sample_stamp_expired:'+topic)
        if 'base' in self.samples and 'joints' in self.samples and abs(self.samples['base'][0]-self.samples['joints'][0])>40_000_000:
            failed.append('base_joint_skew')
        return dict(failed=failed,decision_wall=wall,clock_ns=self.clock_ns,clock_receipt_wall=self.clock_wall,
                    graph_wall=self.graph_wall,counts=dict(self.counts),control=self.control,required=list(self.required),
                    samples={k:dict(stamp_ns=v[0],receipt_wall=v[1],gid=v[2]) for k,v in self.samples.items()})
    def output(self, wall):
        if self.mode=='ARMED':
            if not self._fresh(wall):
                self.trip('INPUT_OR_CLOCK_TIMEOUT');self.fault_details=self.freshness_details(wall)
            elif self.last_output_wall is not None and (wall<self.last_output_wall or wall-self.last_output_wall>self.timeout_s):self.trip('CONTROL_TIMER_GAP')
        if self.mode!='ARMED':return Decision(0.,0.,self.clock_ns,self.mode,self.fault)
        # Simulation seconds govern the command slew; wall time only governs liveness.
        dt=min(.1,max(0.,(self.clock_ns-self.last_output_clock_ns)/1e9))
        def slew(previous,target,rate):return previous+max(-rate*dt,min(rate*dt,target-previous))
        vx=slew(self.last_values[0],self.values[0],.30);wz=slew(self.last_values[1],self.values[1],.50)
        self.last_values=(vx,wz);self.last_output_wall=wall;self.last_output_clock_ns=self.clock_ns
        return Decision(vx,wz,self.samples[self.control][0],self.mode,self.fault)
