"""Known-target map lifecycle from the original native physical hold authority."""
import math


class TargetMapGate:
    def __init__(self):
        self.owner=None;self.session=None;self.removed=False;self.event=None;self.fault=''
        self.last_receipt=None;self.last_phase=None;self.last_stamp=None;self.last_sequence=0

    def observe(self,row,owner,now):
        if self.fault:return False
        try:
            if (not isinstance(row,dict) or not isinstance(owner,str) or not owner
                or not isinstance(row.get('session'),str) or not row['session']
                or type(row.get('stamp_ns')) is not int or row['stamp_ns']<=0
                or not math.isfinite(now) or not math.isfinite(row['decision_wall'])
                or not 0<=now-row['decision_wall']<=.3):return False
            if self.owner is None:self.owner,self.session=owner,row['session']
            if owner!=self.owner or row['session']!=self.session:
                self.fault='MAP_STATUS_OWNER_OR_SESSION_REPLACED';return False
            if row.get('fault') or row.get('phase') in ('FAULT','REVOKED'):
                self.fault='MAP_NATIVE_AUTHORITY_LOST';return False
            sequence=row.get('sequence')
            if type(sequence) is not int or sequence<0:return False
            if (self.last_stamp is not None and row['stamp_ns']<self.last_stamp
                or sequence<self.last_sequence):
                self.fault='MAP_NATIVE_STATUS_REORDER';return False
            self.last_stamp=row['stamp_ns'];self.last_sequence=sequence
            self.last_receipt=now;self.last_phase=row.get('phase')
            if self.removed:return False
            if not (row.get('phase')=='CARRY_ARMED' and row.get('task_phase')=='CARRY_ARMED'
                    and row.get('transport_stage')=='ARMED' and sequence>0):return False
            if not all(isinstance(row.get(k),str) and row[k] for k in ('goal_id','transport_goal_id')):return False
            if row['goal_id']==row['transport_goal_id']:return False
            capture=row.get('capture_health_ns')
            if type(capture) is not int or not -25_000_000<=row['stamp_ns']-capture<=300_000_000:return False
            contacts=row.get('gripper_target_contacts',{})
            if not all(type(contacts.get(f)) in (float,int) and math.isfinite(contacts[f]) and contacts[f]>.005 for f in ('link7','link8')):return False
            if row.get('gripper_force_hold',{}).get('ready') is not True:return False
            self.event={k:row[k] for k in ('session','goal_id','transport_goal_id','stamp_ns','decision_wall','sequence')}
            self.event.update(source_gid=owner,receipt_wall=now)
            self.removed=True;return True
        except (KeyError,TypeError,ValueError):return False

    def snapshot(self):
        return dict(removed=self.removed,fault=self.fault,event=None if self.event is None else dict(self.event),
                    last_receipt_wall=self.last_receipt,last_phase=self.last_phase)


def attestation_matches(value,session,goal,transport_goal,now):
    try:
        event=value['event'];receipt=value['last_receipt_wall']
        return (value.get('removed') is True and not value.get('fault')
            and value.get('last_phase')=='CARRY_ARMED' and math.isfinite(receipt)
            and 0<=now-receipt<=.3 and event['session']==session
            and event['goal_id']==goal and event['transport_goal_id']==transport_goal
            and isinstance(event.get('source_gid'),str) and bool(event['source_gid']))
    except (KeyError,TypeError,ValueError):return False


def occupancy_data(objects,width=120,height=100,resolution=.05,origin=(-2.,-2.5)):
    ox,oy=origin
    return [100 if any(abs(ox+(x+.5)*resolution-p[0])<=half[0]+resolution/2
                      and abs(oy+(y+.5)*resolution-p[1])<=half[1]+resolution/2
                      for _,p,half in objects) else 0
            for y in range(height) for x in range(width)]


def target_cell_clear(costmap,target):
    try:
        if costmap.header.frame_id!='reuse/map':return False
        m=costmap.metadata;resolution=m.resolution
        if not math.isfinite(resolution) or resolution<=0:return False
        x=int(math.floor((target[0]-m.origin.position.x)/resolution))
        y=int(math.floor((target[1]-m.origin.position.y)/resolution))
        return (0<=x<m.size_x and 0<=y<m.size_y and len(costmap.data)==m.size_x*m.size_y
                and 0<=costmap.data[y*m.size_x+x]<254)
    except (AttributeError,IndexError,TypeError,ValueError,OverflowError):return False
