"""Opt-in engine-local lease enforcement, fed by native DDS receipt metadata."""
import json
import math
import time
import uuid
import os
from std_msgs.msg import String
from ch13_navigation_reuse.command_gateway import N
from ch13_navigation_reuse.wire import decode
from .lease import Lease
from ch13_navigation_reuse.callback_timing import timed_callback

CHANNELS=('mission_lease','manipulation_observation','manipulation_navigation','manipulation_gateway','manipulation_goals')


class EngineExtension:
    def __init__(self, node):
        self.node = node
        self.lease = Lease(str(uuid.uuid4()))
        if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
            from ch13_system_validation.transport import TransportLease
            self.lease=TransportLease(self.lease.session)
        self.goals = {}
        self.navigation = None
        self.navigation_receipt = None
        self.gateway=None;self.gateway_receipt=None
        self.graph = {}
        self.graph_wall = None
        self.events = []
        self.last_phase = None
        self.anchor = None
        self.rx_wall={}
        self.status = {'session': self.lease.session, 'phase':'WAITING', 'fault':''}
        self.channels=CHANNELS+(('manipulation_capture_health',) if hasattr(self.lease,'observe_capture') else ())
        for channel in self.channels:
            node.create_subscription(String,N+'/ingress/manipulation/'+channel,
                                     lambda packet,key=channel:self.packet(packet,key),1)
        self.publisher = node.create_publisher(String,N+'/manipulation/status',1)
        from .action_bridge import ActionBridge
        self.actions = ActionBridge(self)

    @timed_callback('manipulation.packet',channel_index=1)
    def packet(self, packet, channel):
        with self.node.lock:
            try:
                key, msg, info = decode(packet.data)
                if key!=channel:raise ValueError('manipulation relay channel mismatch')
                if self.lease.owner('relay:'+channel, info['relay_gid']):
                    return
                self.rx_wall[key]=time.monotonic()
                owner = info['publisher_gid'].hex()
                receipt = info['receipt_wall']
                if key == 'mission_lease':
                    self.lease.heartbeat(json.loads(msg.data),owner,receipt)
                elif key == 'manipulation_observation':
                    self.lease.observe(json.loads(msg.data),owner,receipt)
                elif key == 'manipulation_capture_health':
                    self.lease.observe_capture(json.loads(msg.data),owner,receipt)
                elif key == 'manipulation_navigation':
                    if self.lease.owner('navigation',owner):
                        return
                    self.navigation = json.loads(msg.data)
                    self.navigation_receipt = receipt
                elif key == 'manipulation_gateway':
                    if self.lease.owner('gateway',owner):return
                    self.gateway=json.loads(msg.data);self.gateway_receipt=receipt
                elif key == 'manipulation_goals':
                    if self.lease.owner('nav_action_status',owner):
                        return
                    self.goals = {bytes(s.goal_info.goal_id.uuid).hex():int(s.status) for s in msg.status_list}
                else:
                    self.lease.trip('UNEXPECTED_MANIPULATION_CHANNEL')
            except (ValueError,TypeError,KeyError) as exc:
                self.lease.trip('INVALID_MANIPULATION_INGRESS:'+str(exc))

    @timed_callback('manipulation.monitor')
    def monitor(self):
        now = time.monotonic()
        counts = {key:self.node.count_publishers(topic) for key,topic in (
            ('mission',N+'/manipulation/lease'),('observer',N+'/vision/observation'),
            ('navigation',N+'/navigation/status'),
            ('nav_status','/navigate_to_pose/_action/status'),('gateway',N+'/gateway/status'))}
        if hasattr(self.lease,'observe_capture'):counts['capture_health']=self.node.count_publishers(N+'/vision/health')
        counts.update({key:self.node.count_publishers(N+'/ingress/manipulation/'+key) for key in self.channels})
        with self.node.lock:
            self.graph,self.graph_wall = counts,now
            for key,count in counts.items():
                if count>1:
                    self.lease.trip('DUPLICATE_OWNER:'+key)
            status = dict(self.status)
        self.publisher.publish(String(data=json.dumps(status)))
        self.actions.monitor()

    def before(self,p,decision,clock_ns):
        with self.node.lock:
            self.actions.before(p,clock_ns)

    def step(self, p, decision, q, v, state, tilt):
        with self.node.lock:
            # Receipt callbacks share this lock. Sample after acquiring it so a
            # newly delivered receipt cannot appear to come from the future.
            now, clock = time.monotonic(),state['stamp_ns']
            supported = (decision.mode=='ARMED' and decision.vx==0 and decision.wz==0
                         and math.hypot(v[0],v[1])<=.05 and abs(v[5])<=.20 and tilt<=.35)
            if self.lease.message is not None and self.lease.phase not in ('REVOKED','FAULT'):
                if (self.gateway_receipt is None or not 0<=now-self.gateway_receipt<=.30
                        or self.gateway.get('mode')!='ARMED' or self.gateway.get('fault')):
                    self.lease.trip('GATEWAY_NOT_HEALTHY')
                if self.graph_wall is None or now-self.graph_wall>.30 or any(c!=1 for c in self.graph.values()):
                    self.lease.trip('MANIPULATION_GRAPH_LOST')
            nav_idle = (self.navigation is not None and self.navigation_receipt is not None
                        and 0<=now-self.navigation_receipt<=.30
                        and self.navigation.get('phase')=='IDLE'
                        and self.navigation.get('output_held') and not self.navigation.get('fault'))
            pose = [float(q[0]),float(q[1]),state['yaw']]
            if hasattr(self.lease,'motion_inputs'):
                contacts=(all(self.pick_monitor.forces.get(f,0.)>.005 for f in ('link7','link8'))
                    and self.actions.gripper_hold.status()['ready'])
                support_force=getattr(self.pick_monitor,'support_N',0.)
                scenario=getattr(self.pick_monitor,'scenario',None)
                receiving_support=(support_force>.01 if scenario is None else scenario.receiving_support_ready(support_force,self.lease.observation))
                self.lease.motion_inputs(armed=decision.mode=='ARMED',
                    moving_supported=tilt<=.20 and math.hypot(v[0],v[1])<=.30 and abs(v[5])<=.35,
                    contacts=contacts,busy=self.actions.busy,
                    support=receiving_support)
            phase = self.lease.evaluate(clock,now,settled=self.node.ready_now(),supported=supported,
                                        goal_status=self.goals,actual_pose=pose,navigation_idle=nav_idle)
            if phase=='READY' and self.anchor is None:
                self.anchor = pose
            if self.anchor is not None and phase in ('READY','EXECUTING') and getattr(self.lease,'stage','PICK')=='PICK':
                drift = math.hypot(pose[0]-self.anchor[0],pose[1]-self.anchor[1])
                yaw_drift = abs(math.atan2(math.sin(pose[2]-self.anchor[2]),math.cos(pose[2]-self.anchor[2])))
                if drift>.03 or yaw_drift>.10:
                    phase = self.lease.trip('MANIPULATION_BASE_DRIFT')
            if getattr(self.lease,'stage','PICK')!='PICK' and self.lease.fault:
                self.node.guard.trip('TRANSPORT:'+self.lease.fault)
            self.status = dict(session=self.lease.session,phase=phase,fault=self.lease.fault,
                               goal_id=self.lease.goal_id,stamp_ns=clock,decision_wall=now,
                               sequence=self.lease.sequence,owners=dict(self.lease.owners),
                               capture_ns=None if self.lease.observation is None else self.lease.observation['capture_ns'],
                               task_phase='WAITING' if self.lease.message is None else self.lease.message.get('task_phase','WAITING'))
            self.status.update(mission_receipt_wall=self.lease.mission_receipt,
                               observation_receipt_wall=self.lease.observation_receipt,gateway_receipt_wall=self.gateway_receipt,
                               channel_processed_wall=dict(self.rx_wall))
            if hasattr(self,'pick_monitor'):
                self.status['gripper_target_contacts']=dict(self.pick_monitor.forces)
                self.status['gripper_force_hold']=self.actions.gripper_hold.status()
                self.status['target_support_N']=getattr(self.pick_monitor,'support_N',0.)
            if hasattr(self.lease,'stage'):
                self.status['transport_stage']=self.lease.stage
                self.status['transport_goal_id']=self.lease.transport_goal
                self.status['transport_observation_contract']='continuous_tactile_hold_and_fresh_capture_v1; fresh_3D_required_for_place'
                self.status['capture_health_ns']=None if self.lease.capture_health is None else self.lease.capture_health['capture_ns']
            if phase != self.last_phase:
                self.events.append(dict(self.status))
                self.last_phase = phase
            self.actions.after(p,state,q,v)

    def summary(self):
        return dict(control_profile='13_6_model_bias_v2',last_status=self.status,events=self.events,arm_events=self.actions.events,
                    arm_observations=self.actions.rows,gripper_force_profile='contact_force_hold_v1' if hasattr(self,'pick_monitor') else 'position_PD',
                    gripper_force_events=self.actions.gripper_hold.events)
