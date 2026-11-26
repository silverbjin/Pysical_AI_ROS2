"""Immutable observations, original ROS stamp and independent receipt clock."""
from dataclasses import dataclass
import math
@dataclass(frozen=True)
class Target:
    mission_id:str
    epoch:int
    source:str
    object_class:str
    frame:str
    stamp_ns:int
    position:tuple
    orientation:tuple
    pose_kind:str
    received:float

class BlackboardContext:
    def __init__(self,mission_id,epoch):
        self.mission_id=mission_id;self.epoch=epoch;self.snapshot=None;self.reason='no_observation'
        self.ros_ns=None;self.advance_at=None;self.clock_valid=False;self.settle_ns=0;self.rewound=False
    def invalidate(self,reason):
        self.snapshot=None;self.reason=reason;return False
    def clock(self,ros_ns,now):
        if ros_ns<=0:self.clock_valid=False;return self.invalidate('zero_clock')
        if self.ros_ns is not None and ros_ns<self.ros_ns:
            self.rewound=True;self.clock_valid=False;self.ros_ns=ros_ns;return self.invalidate('rewind')
        if self.ros_ns is None or ros_ns>self.ros_ns:self.advance_at=now
        self.ros_ns=ros_ns;self.clock_valid=not self.rewound and self.advance_at is not None and now-self.advance_at<=.2
        if not self.clock_valid:return self.invalidate('pause_or_rewind')
        return True
    def mark_settled(self):
        self.settle_ns=self.ros_ns or 0;self.invalidate('fresh_after_settle_required')
    def write_observation(self,msg,tf_available,now):
        """One decoder for executor and actual DDS contract fixture."""
        def ns(stamp):return int(stamp.sec)*1000000000+int(stamp.nanosec)
        p=msg.target_pose.pose.position;q=msg.target_pose.pose.orientation
        t=Target(msg.mission_id,msg.epoch,msg.source,msg.object_class,msg.target_pose.header.frame_id,ns(msg.target_pose.header.stamp),(p.x,p.y,p.z),(q.x,q.y,q.z,q.w),msg.pose_kind,now)
        if not msg.valid or ns(msg.header.stamp)!=t.stamp_ns or msg.header.frame_id!=t.frame:return self.invalidate('invalid_header')
        return self.write_target(t,tf_available,now)
    def write_target(self,pose_stamped,tf_available=True,now=None):
        t=pose_stamped # typed immutable snapshot, not a raw unlabelled pose
        if not isinstance(t,Target):return self.invalidate('untyped')
        if not self.clock_valid:return self.invalidate('invalid_clock')
        if t.mission_id!=self.mission_id or t.epoch!=self.epoch:return self.invalidate('mission_epoch')
        if t.source!='MOCK' or t.object_class!='red_cube' or t.pose_kind!='GRASP_POSE':return self.invalidate('source_or_kind')
        if t.frame!='map' or not tf_available:return self.invalidate('frame_or_tf')
        if t.stamp_ns<=0 or t.stamp_ns>self.ros_ns or self.ros_ns-t.stamp_ns>300000000 or t.stamp_ns<=self.settle_ns:return self.invalidate('stamp')
        if len(t.position)!=3 or len(t.orientation)!=4 or not all(math.isfinite(x) for x in (*t.position,*t.orientation)) or abs(sum(x*x for x in t.orientation)-1)>1e-6:return self.invalidate('nonfinite_or_quaternion')
        if now is None or not 0<=now-t.received<=.3:return self.invalidate('receipt')
        self.snapshot=t;self.reason='';return True
    def read(self,now,tf_available=True):
        t=self.snapshot
        if t is None:return None
        return t if self.write_target(t,tf_available,now) else None
