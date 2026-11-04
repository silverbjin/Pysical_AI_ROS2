"""Opt-in moving hold authority, distinct from a stationary manipulation lease."""
import copy
import math
from ch13_manipulation_reuse.lease import Lease


class TransportLease(Lease):
    def __init__(self,session):
        super().__init__(session)
        self.stage='PICK';self.transport_goal=None;self.transport_target=None
        self.motion={};self.last_settled=False;self.place_anchor=None
        self.capture_health=None;self.capture_receipt=None;self.place_step='PLACE_WAIT'

    def motion_inputs(self,**values):self.motion=values

    def observe_capture(self,sample,owner,receipt):
        if self.fault or self.owner('capture_health',owner):return False
        try:
            if (not isinstance(sample,dict) or type(sample.get('capture_ns')) is not int
                or sample['capture_ns']<=0 or sample.get('scope')!='validated_RGBD_capture_and_past_TF'
                or not all(math.isfinite(v) for v in (sample['capture_wall'],receipt))
                or sample['capture_wall']>receipt+.01):raise ValueError('invalid original capture health')
            if self.capture_health is not None:
                if sample['capture_ns']<self.capture_health['capture_ns']:return self.trip('CAPTURE_HEALTH_REORDER')
                if sample['capture_ns']==self.capture_health['capture_ns']:
                    if sample!=self.capture_health:self.trip('CAPTURE_HEALTH_CHANGED')
                    return False
            self.capture_health=copy.deepcopy(sample);self.capture_receipt=receipt;return True
        except (KeyError,TypeError,ValueError):
            self.trip('INVALID_CAPTURE_HEALTH');return False

    def capture_fresh(self,clock_ns,wall):
        sample=self.capture_health
        return (sample is not None and 0<=wall-self.capture_receipt<=.3
            and 0<=wall-sample['capture_wall']<=.3
            and -25_000_000<=clock_ns-sample['capture_ns']<=300_000_000)

    def heartbeat(self,message,owner,receipt):
        if self.fault or self.phase=='REVOKED':return False
        if not isinstance(message,dict):
            self.trip('INVALID_TRANSPORT_HEARTBEAT');return False
        task=message.get('task_phase','WAITING')
        if self.stage=='PICK' and task!='CARRY_ARMED':return super().heartbeat(message,owner,receipt)
        if self.owner('mission',owner):return False
        try:
            if message['session']!=self.session:return self.trip('SESSION_MISMATCH')
            if (type(message['sequence']) is not int or message['sequence']<=0
                or type(message['stamp_ns']) is not int or message['stamp_ns']<=0
                or type(message['capture_ns']) is not int or not math.isfinite(receipt)
                or message['goal_id']!=self.goal_id or message['target']!=self.message['target']
                or message['terminal']!=4 or message['state'] not in ('OFFER','REVOKE')):
                raise ValueError('invalid transport heartbeat')
            if message['sequence']<=self.sequence:return False
            if message['stamp_ns']<self.message['stamp_ns']:return self.trip('MISSION_CLOCK_REORDER')
            if message['state']=='REVOKE':
                self.phase='REVOKED';return True
            goal=message['transport_goal_id'];target=message['transport_target']
            if not isinstance(goal,str) or not goal or goal==self.goal_id or len(target)!=3 or not all(math.isfinite(v) for v in target):
                raise ValueError('invalid reserved goal')
            if self.transport_goal is not None and (goal!=self.transport_goal or target!=self.transport_target):
                return self.trip('TRANSPORT_RESERVATION_CHANGED')
            if self.stage=='PICK':
                if (self.phase!='READY' or not self.last_settled or self.motion.get('busy')
                    or not self.motion.get('contacts') or self.message.get('task_phase') not in ('HOLD','POST_SETTLE')):
                    return self.trip('TRANSPORT_NOT_SETTLED_HELD')
                self.transport_goal,self.transport_target=goal,list(target)
                self.stage='ARMED';self.phase='CARRY_ARMED'
            allowed={'ARMED':('CARRY_ARMED','CARRY'),'CARRY':('CARRY','PLACE_WAIT'),
                     'PLACE_WAIT':('PLACE_WAIT',),'PLACE':('PLACE_WAIT','LOWER','RELEASE','RETREAT')}
            if task not in allowed.get(self.stage,()):return self.trip('INVALID_TRANSPORT_TRANSITION')
            if self.stage=='PLACE':
                next_step={'PLACE_WAIT':'LOWER','LOWER':'RELEASE','RELEASE':'RETREAT','RETREAT':None}
                if task!=self.place_step and task!=next_step[self.place_step]:return self.trip('INVALID_PLACE_ORDER')
                self.place_step=task
            if task=='CARRY':self.stage='CARRY';self.phase='CARRY'
            elif task=='PLACE_WAIT' and self.stage!='PLACE':self.stage='PLACE_WAIT'
            if task=='RELEASE' and not self.motion.get('support'):return self.trip('RELEASE_WITHOUT_SUPPORT')
            self.message=copy.deepcopy(message);self.sequence=message['sequence'];self.mission_receipt=receipt
            return True
        except (KeyError,TypeError,ValueError):
            self.trip('INVALID_TRANSPORT_HEARTBEAT');return False

    def evaluate(self,clock_ns,wall,*,settled,supported,goal_status,actual_pose,navigation_idle):
        self.last_settled=settled
        if self.stage=='PICK':return super().evaluate(clock_ns,wall,settled=settled,supported=supported,
            goal_status=goal_status,actual_pose=actual_pose,navigation_idle=navigation_idle)
        # During fixed-arm transport, a point may become occluded. It remains
        # expired; only fresh camera health + continuous tactile hold authorize
        # the pre-reserved navigation goal. Arm work requires fresh 3D again.
        if not self.fresh(clock_ns,wall,require_observation=self.stage=='PLACE'):return self.phase
        if not self.capture_fresh(clock_ns,wall):return self.trip('CAPTURE_HEALTH_EXPIRED')
        if any(g not in (self.goal_id,self.transport_goal) and s in (1,2,3) for g,s in goal_status.items()):
            return self.trip('UNRESERVED_NAV_GOAL')
        if goal_status.get(self.goal_id)!=4:return self.trip('OUTBOUND_TERMINAL_CHANGED')
        if not self.motion.get('armed') or not self.motion.get('moving_supported'):
            return self.trip('TRANSPORT_PLATFORM_UNSAFE')
        task=self.message['task_phase']
        if task not in ('RELEASE','RETREAT') and not self.motion.get('contacts'):
            return self.trip('TRANSPORT_CONTACT_LOST')
        if self.stage in ('ARMED','CARRY','PLACE_WAIT') and self.motion.get('busy'):
            return self.trip('ARM_ACTION_DURING_CARRY')
        current=goal_status.get(self.transport_goal)
        if current in (5,6):return self.trip('RETURN_GOAL_FAILED')
        if (self.stage=='PLACE_WAIT' and current==4 and navigation_idle and settled and supported
            and self.observation_fresh(clock_ns,wall)):
            # The new stationary authority is admitted once, from measured return.
            target=self.transport_target
            if (math.hypot(actual_pose[0]-target[0],actual_pose[1]-target[1])>.10
                or abs(math.atan2(math.sin(actual_pose[2]-target[2]),math.cos(actual_pose[2]-target[2])))>.10):
                return self.trip('PLACE_POSE_MISMATCH')
            self.stage='PLACE';self.phase='READY';self.place_anchor=list(actual_pose)
        if self.stage=='PLACE':
            if current!=4 or not navigation_idle or not supported:return self.trip('PLACE_BASE_NOT_ZERO')
            if (math.hypot(actual_pose[0]-self.place_anchor[0],actual_pose[1]-self.place_anchor[1])>.03
                or abs(math.atan2(math.sin(actual_pose[2]-self.place_anchor[2]),math.cos(actual_pose[2]-self.place_anchor[2])))>.10):
                return self.trip('PLACE_BASE_DRIFT')
        return self.phase
