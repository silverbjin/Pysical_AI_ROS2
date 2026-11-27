"""Read-only display contract. No ROS or robot commands."""
import math

MAX_AGE_NS = 300_000_000
TARGET_NS = 'ch15_target'
STATUS_NS = 'ch15_status'

def stamp_ns(stamp):
    return int(stamp.sec)*1_000_000_000+int(stamp.nanosec)

def fresh(stamp, now):
    return 0 < stamp <= now and now-stamp <= MAX_AGE_NS

def valid_target(msg, frame, identity, mode, now):
    p=msg.target_pose.pose.position
    q=msg.target_pose.pose.orientation
    h=msg.target_pose.header
    source_kind={'mock':('MOCK','GRASP_POSE'),'physical':('RGBD_COLOR','POSITION_ONLY')}
    return (mode in source_kind and msg.valid and bool(msg.mission_id)
            and (msg.mission_id,msg.epoch)==identity
            and (msg.source,msg.pose_kind)==source_kind[mode]
            and msg.object_class=='red_cube'
            and h.frame_id==frame==msg.header.frame_id
            and stamp_ns(h.stamp)==stamp_ns(msg.header.stamp)
            and fresh(stamp_ns(h.stamp),now)
            and all(math.isfinite(v) for v in (p.x,p.y,p.z,q.x,q.y,q.z,q.w))
            and abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)<=1e-6)

class Session:
    """Retire prior identity; rewind is fail-closed until node restart."""
    def __init__(self, mode, physical_id='cube_lab'):
        if mode not in ('mock','physical','replay') or not physical_id:
            raise ValueError('invalid display mode')
        self.mode=mode
        self.identity=(physical_id,0) if mode=='physical' else None
        self.retired=set()
        self.last_clock=None
        self.rewound=False

    def clock(self, now):
        if self.last_clock is not None and now<self.last_clock:
            self.rewound=True
            self.identity=None
        self.last_clock=now
        return now>0 and not self.rewound

    def status(self,msg,now):
        key=(msg.mission_id,msg.epoch)
        if (self.mode=='physical' or self.rewound or msg.source!='MOCK'
                or msg.profile!='mock' or not key[0] or key in self.retired
                or not fresh(stamp_ns(msg.header.stamp),now)):
            return False,False
        if self.identity and key[0]==self.identity[0] and key[1]<self.identity[1]:
            return False,False
        changed=key!=self.identity
        if changed and self.identity is not None:
            self.retired.add(self.identity)
        self.identity=key
        return True,changed
