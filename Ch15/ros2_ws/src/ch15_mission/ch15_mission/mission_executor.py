"""G03 actual DDS mock mission. Single-thread callbacks; supervisor timer independent of BT."""
import csv,json,math,os,pathlib,time
from uuid import uuid4
import py_trees
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.clock import Clock,ClockType
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped,Twist
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import Bool,String
from std_srvs.srv import Trigger
from unique_identifier_msgs.msg import UUID
from tf2_ros import Buffer,TransformListener
from ch15_interfaces.action import PickObject,PlaceObject
from ch15_interfaces.srv import SwitchGait
from ch15_interfaces.msg import ReadyState,SafetyState,MissionStatus,TargetObservation,MissionEvent
from ch15_adapters.qos_profiles import profile,state_qos
from .action_supervisor import ActionSupervisor,TERMINAL
from .blackboard_context import BlackboardContext,Target
from .behaviours import Task
from .mission_tree import create_root
from .recovery import reset_allowed,outcome

ST=py_trees.common.Status
STATES={'ready':'IDLE','navigate':'NAVIGATING','detect':'SEARCHING','approach_stand':'APPROACHING','pick_retract':'MANIPULATING','return_home':'RETURNING','place':'PLACING'}
KEYS=('fault_latched','safe_abort','ready','navigate','detect','approach_stand','pick_retract','return_home','place','verify_finish')
BUSINESS=KEYS[3:]
def ns(stamp):return int(stamp.sec)*1000000000+int(stamp.nanosec)

class MissionExecutor(Node):
    def __init__(self):
        super().__init__('ch15_mission_executor')
        self.auto=self.declare_parameter('auto_start',False).value
        name=self.declare_parameter('evidence_dir','').value
        self.out=pathlib.Path(name) if name else pathlib.Path.home()/'.ros/ch15'/uuid4().hex
        self.out.mkdir(parents=True,exist_ok=True)
        self.events=(self.out/'mission-events.jsonl').open('x')
        self.ticks=(self.out/'ticks.csv').open('x',newline='')
        self.writer=csv.writer(self.ticks);self.writer.writerow(['tick','steady_ns','duration_ms','root_status'])
        self.seq=0;self.tick_count=0;self.started=False;self.finished=False;self.fault='';self.block=True;self.state='IDLE';self.epoch=0;self.mission_id=uuid4().hex
        self.started_at=0.;self.setup_at=time.monotonic();self.held=False;self.completed=[];self.tasks={};self.entered={};self.witnesses={};self.requests={}
        self.ready_count=0;self.ready_at=0.;self.safe_at=0.;self.safety=None;self.gait='';self.gait_at=0.;self.motion_at=0.;self.zero_since=None;self.zero_count=0;self.start_requested=False
        self.bb=BlackboardContext(self.mission_id,self.epoch)
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.status_pub=self.create_publisher(MissionStatus,'/ch15/mission_state',state_qos)
        self.event_pub=self.create_publisher(MissionEvent,'/ch15/mission_event',profile(100))
        self.block_pub=self.create_publisher(Bool,'/ch15/mission_block',profile(10))
        self.target_pub=self.create_publisher(PoseStamped,'/ch15/target_pose',profile())
        self.create_subscription(ReadyState,'/ch15/ready',self.on_ready,profile())
        self.create_subscription(SafetyState,'/ch15/safety_state',self.on_safety,state_qos)
        self.create_subscription(Twist,'/cmd_vel',self.on_motion,profile())
        self.create_subscription(String,'/ch15/gait_state',self.on_gait,profile(transient=True))
        self.create_subscription(String,'/ch15/mock_goal_witness',self.on_witness,profile(20))
        self.create_subscription(TargetObservation,'/ch15/target_observation',self.on_target,profile())
        self.gait_client=self.create_client(SwitchGait,'/switch_gait')
        self._action_clients={k:ActionClient(self,a,n) for k,a,n in [('nav',NavigateToPose,'/navigate_to_pose'),('pick',PickObject,'/pick_object'),('place',PlaceObject,'/place_object')]}
        self.sup={k:ActionSupervisor(c,lambda x:UUID(uuid=list(bytes.fromhex(x))),lambda uid,k=k:self.valid_witness(uid,k),emit=self.emit,block=self.trigger_fault,timeout=5.) for k,c in self._action_clients.items()}
        self.create_service(Trigger,'/ch15/start_mission',self.start)
        self.create_service(Trigger,'/ch15/cancel_mission',self.cancel)
        self.create_service(Trigger,'/ch15/reset_safety',self.reset)
        self.make_tree()
        clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.02,self.supervise,clock=clock)
        self.create_timer(.05,self.heartbeat,clock=clock)
        self.create_timer(.1,self.tick,clock=clock)
    def make_tree(self):
        self.root=create_root('mock',{k:Task(k,self) for k in KEYS})
        self.tree=py_trees.trees.BehaviourTree(self.root)
    def emit(self,event,request_id='',goal_uuid='',**detail):
        self.seq+=1;m=MissionEvent();m.header.stamp=self.get_clock().now().to_msg();m.mission_id=self.mission_id;m.epoch=self.epoch;m.producer='ch15_mission_executor';m.event_seq=self.seq;m.steady_ns=time.monotonic_ns();m.event=event;m.request_id=request_id;m.goal_uuid=goal_uuid;m.source='MOCK';m.detail=json.dumps(detail,sort_keys=True)
        self.event_pub.publish(m)
        self.events.write(json.dumps(dict(mission_id=m.mission_id,epoch=m.epoch,producer=m.producer,event_seq=m.event_seq,steady_ns=m.steady_ns,ros_ns=ns(m.header.stamp),event=event,request_id=request_id,goal_uuid=goal_uuid,source='MOCK',detail=detail))+'\n');self.events.flush()
    def on_ready(self,m):
        self.ready_count=min(3,self.ready_count+1) if m.ready else 0;self.ready_at=time.monotonic()
    def on_safety(self,m):self.safety=m;self.safe_at=time.monotonic()
    def on_motion(self,m):
        now=time.monotonic();self.motion_at=now
        v=m.linear;w=m.angular;zero=all(math.isfinite(x) and abs(x)<=1e-9 for x in (v.x,v.y,v.z,w.x,w.y,w.z))
        if zero:
            if self.zero_since is None:self.zero_since=now;self.zero_count=0
            self.zero_count+=1
        else:self.zero_since=None;self.zero_count=0
    def on_gait(self,m):self.gait=m.data;self.gait_at=time.monotonic()
    def on_witness(self,m):
        try:
            row=json.loads(m.data)
            if row['source']=='MOCK' and row['kind'] in self.sup and len(row['uuid'])==32 and type(row['held']) is bool and type(row['placed']) is bool:self.witnesses[row['uuid']]=row
        except (ValueError,KeyError,TypeError):pass
    def valid_witness(self,uid,kind):
        w=self.witnesses.get(uid)
        return bool(w and w['kind']==kind and (kind!='pick' or w['held']) and (kind!='place' or (not w['held'] and w['placed'])))
    def tf_ready(self):return self.tf.can_transform('map','base_link',Time())
    def on_target(self,m):
        if not self.started or self.finished:return
        now=time.monotonic();self.bb.clock(self.get_clock().now().nanoseconds,now);p=m.target_pose.pose.position;q=m.target_pose.pose.orientation
        t=Target(m.mission_id,m.epoch,m.source,m.object_class,m.target_pose.header.frame_id,ns(m.target_pose.header.stamp),(p.x,p.y,p.z),(q.x,q.y,q.z,q.w),m.pose_kind,now)
        if not m.valid or ns(m.header.stamp)!=t.stamp_ns or m.header.frame_id!=t.frame:self.bb.invalidate('invalid_header');return
        if self.bb.write_target(t,self.tf_ready(),now):self.target_pub.publish(m.target_pose)
    def fresh_ready(self):
        now=time.monotonic()
        return self.ready_count==3 and now-self.ready_at<=.3 and self.safety is not None and now-self.safe_at<=.3 and not self.safety.latched and self.safety.owner=='MOCK:ch15_command_arbiter'
    def stopped(self):
        now=time.monotonic();return self.zero_since is not None and now-self.zero_since>=.3 and now-self.motion_at<=.15 and self.zero_count>=6
    def all_terminal(self):return all(s.active is None and all(a.resolved for a in s.rows.values()) for s in self.sup.values())
    def heartbeat(self):
        self.block_pub.publish(Bool(data=self.block))
        m=MissionStatus();m.header.stamp=self.get_clock().now().to_msg();m.mission_id=self.mission_id;m.profile='mock';m.epoch=self.epoch;m.state=self.state;m.error_code='SENSOR_TIMEOUT' if self.fault else 'NONE';m.source='MOCK';m.is_object_grasped=self.held;m.grasp_source='MOCK' if self.held else 'UNKNOWN';m.full_mission_success=False;self.status_pub.publish(m)
    def start(self,req,res):
        res.success=self.begin();res.message='started' if res.success else 'not ready or already used';return res
    def begin(self):
        if self.started or self.finished or not self.fresh_ready() or not self.all_terminal():return False
        self.started=True;self.started_at=time.monotonic();self.block=False;self.emit('START');self.heartbeat();return True
    def cancel(self,req,res):
        res.success=self.started and not self.finished and not self.fault
        if res.success:self.trigger_fault('operator_cancel')
        res.message='cancel requested; await terminal' if res.success else 'no active mission';return res
    def reset(self,req,res):
        ok=self.finished and not self.held and reset_allowed(self.started and not self.finished,not self.all_terminal(),self.stopped(),self.fresh_ready(),any(s.latched for s in self.sup.values()))
        res.success=bool(ok)
        if ok:
            self.epoch+=1;self.mission_id=uuid4().hex;self.bb=BlackboardContext(self.mission_id,self.epoch)
            self.started=False;self.finished=False;self.block=True;self.fault='';self.state='IDLE';self.completed=[];self.entered={};self.tasks={};self.requests={};self.witnesses={};self.setup_at=time.monotonic();self.auto=False;self.make_tree()
        res.message='new epoch; explicit start required' if ok else 'blocked: active/unresolved/held/stale/latched or not stopped; actual safety-latch reset deferred G08';return res
    def trigger_fault(self,reason):
        if not self.fault:self.fault=reason;self.emit('FAULT',reason=reason)
        if not self.block:self.block=True;self.emit('COMMAND_BLOCKED',reason=reason);self.block_pub.publish(Bool(data=True))
    def supervise(self):
        for s in self.sup.values():
            s.tick()
            if self.fault and s.active is not None:s.request_cancel(s.active)
    def enter(self,name):
        if name in ('fault_latched','safe_abort'):return
        if name in self.entered:return
        self.entered[name]=time.monotonic();self.tasks[name]={}
        if name in STATES:self.state=STATES[name]
        self.emit('STEP_ENTER',step=name,state='READY' if name=='ready' else self.state);self.heartbeat()
    def interrupt(self,name):
        if name in self.requests:
            s,rid=self.requests[name];s.request_cancel(rid)
    def done(self,name):
        if name not in self.completed:self.completed.append(name)
        return ST.SUCCESS
    def goal_pose(self,x=1.):
        p=PoseStamped();p.header.frame_id='map';p.header.stamp=self.get_clock().now().to_msg();p.pose.position.x=x;p.pose.orientation.w=1.;return p
    def observed_pose(self,t):
        p=PoseStamped();p.header.frame_id=t.frame;p.header.stamp.sec=t.stamp_ns//1000000000;p.header.stamp.nanosec=t.stamp_ns%1000000000
        p.pose.position.x,p.pose.position.y,p.pose.position.z=t.position;p.pose.orientation.x,p.pose.orientation.y,p.pose.orientation.z,p.pose.orientation.w=t.orientation;return p
    def action(self,name,kind):
        s=self.sup[kind]
        if name not in self.requests:
            if not all(x.active is None for x in self.sup.values()) or not s.ready_for_goal():return ST.RUNNING
            if kind=='nav':
                g=NavigateToPose.Goal();g.pose=self.goal_pose(0. if name=='return_home' else 1.)
            elif kind=='pick':
                t=self.bb.read(time.monotonic(),self.tf_ready())
                if t is None:return ST.FAILURE
                g=PickObject.Goal();g.object_class='red_cube';g.target_pose=self.observed_pose(t);g.timeout_sec=3.
            else:
                g=PlaceObject.Goal();g.target_pose=self.goal_pose(0.);g.timeout_sec=3.
            self.requests[name]=(s,s.send(g));return ST.RUNNING
        _,rid=self.requests[name];v=s.poll(rid)
        if v=='SUCCEEDED_VERIFIED':
            if kind=='pick':self.held=True
            elif kind=='place':self.held=False
            # Deliberate dwell keeps the educational tick trace >=30.
            if time.monotonic()-self.entered[name]>=.4:return self.done(name)
        elif v in TERMINAL:return ST.FAILURE
        return ST.RUNNING
    def step(self,name):
        now=time.monotonic()
        if name=='fault_latched':return ST.SUCCESS if self.fault else ST.FAILURE
        if name=='safe_abort':
            if self.all_terminal() and self.stopped():self.emit('STOP_OBSERVED',kind='MOCK_ZERO',samples=self.zero_count);return ST.SUCCESS
            if any(s.latched and s.active is not None for s in self.sup.values()):return ST.RUNNING
            return ST.RUNNING
        if name=='ready':return self.done(name) if self.fresh_ready() else ST.RUNNING
        if now-self.entered[name]>8.:return ST.FAILURE
        if name in ('navigate','return_home'):return self.action(name,'nav')
        if name=='pick_retract':return self.action(name,'pick')
        if name=='place':return self.action(name,'place')
        if name=='detect':
            return self.done(name) if now-self.entered[name]>=.4 and self.bb.read(now,self.tf_ready()) else ST.RUNNING
        if name=='approach_stand':
            task=self.tasks[name]
            if 'gait' not in task:
                if not self.gait_client.service_is_ready():return ST.RUNNING
                task['gait']=self.gait_client.call_async(SwitchGait.Request(gait_type='stand'));return ST.RUNNING
            if not task['gait'].done():return ST.RUNNING
            if not task['gait'].result().success:return ST.FAILURE
            if self.gait!='stand' or now-self.gait_at>.3 or not self.stopped():return ST.RUNNING
            if 'settled' not in task:
                self.bb.mark_settled();task['settled']=True;self.emit('STOP_OBSERVED',kind='MOCK_ZERO',samples=self.zero_count);return ST.RUNNING
            return self.done(name) if now-self.entered[name]>=.5 and self.bb.read(now,self.tf_ready()) else ST.RUNNING
        if name=='verify_finish':
            if not self.all_terminal() or self.held or not self.stopped() or now-self.entered[name]<.5:return ST.RUNNING
            return self.done(name)
        return ST.FAILURE
    def finish(self,state):
        if self.finished:return
        self.block=True;self.block_pub.publish(Bool(data=True));self.finished=True;self.state=state
        self.emit('END',state=state,mock_mission_success=state=='COMPLETED',full_mission_success=False,steps=self.completed,all_terminal=self.all_terminal())
        self.heartbeat()
    def tick(self):
        now=time.monotonic();self.bb.clock(self.get_clock().now().nanoseconds,now)
        if not self.started:
            if self.auto and now-self.setup_at<=15.:self.begin()
            return
        if self.finished:return
        if not self.fresh_ready():self.trigger_fault('readiness_or_safety_lost')
        if now-self.started_at>60.:self.trigger_fault('mission_deadline')
        if not self.bb.clock_valid:self.trigger_fault('clock_invalid')
        a=time.monotonic_ns()
        try:self.tree.tick()
        except Exception as exc:self.trigger_fault('tree_exception:'+str(exc));return
        elapsed=(time.monotonic_ns()-a)/1e6;self.tick_count+=1;self.writer.writerow([self.tick_count,a,elapsed,self.root.status.name]);self.ticks.flush()
        if self.root.status==ST.FAILURE:self.trigger_fault('task_failure')
        if self.root.status==ST.SUCCESS:
            normal=self.completed==['ready',*BUSINESS] and self.all_terminal() and self.stopped() and not self.held
            self.finish(outcome(True,normal,bool(self.fault)))
        if self.fault and any(s.latched and s.active is not None for s in self.sup.values()):
            # Do not claim clean ABORTED while a UUID terminal is unknown.
            self.finish('ERROR')
    def close(self):
        self.events.close();self.ticks.close()
def main():
    rclpy.init();n=MissionExecutor()
    try:rclpy.spin(n)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        clean=n.all_terminal() and (not n.started or n.finished)
        n.close();n.destroy_node();rclpy.try_shutdown()
    if not clean:raise SystemExit(2)
