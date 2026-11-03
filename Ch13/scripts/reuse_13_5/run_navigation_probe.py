"""Owned Nav2+MuJoCo probe. Action terminals and measured stop are separate."""
import argparse,json,math,os,re,signal,subprocess,sys,time,traceback
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry,Path as NavPath,OccupancyGrid
from sensor_msgs.msg import JointState
from rclpy.qos import QoSProfile,DurabilityPolicy
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from std_srvs.srv import Trigger
from ch13_navigation_reuse.command_gateway import N,ns,set_stamp
from run_r2_probe import service_call

def yaw(q):return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
class _StartupComplete(Exception):pass

def main(argv=None,handoff=None,planning=False,pick_scene=False,startup_only=False):
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--evidence',required=True);ap.add_argument('--vision-hz',type=int,choices=[10,15],default=10);ap.add_argument('--case',choices=['free','obstacle','blocked','cancel','raw_loss','vision'],default='free');args=ap.parse_args(argv)
 if handoff is not None and args.case!='vision':raise ValueError('live manipulation requires vision mission')
 root=Path(args.repo_root);out=Path(args.evidence);out.mkdir(parents=True,exist_ok=True);scene=args.case if args.case in ['obstacle','blocked','vision'] else 'free'
 S={'result':'FAIL','case':args.case,'events':[]};node=None;launch=None;log=None;goal_handle=None;result_future=None;clock_ns=0;state=None;gateway={};platform={};boundary={};poses=[];plans=[];clients={};observation=None;joints=None;grid=None;vision_status={};arm_model=None;vision_record=None;paused_pid=None
 try:
  (out/'boot_id.txt').write_text(Path('/proc/sys/kernel/random/boot_id').read_text());log=(out/'launch.log').open('w')
  launch=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch','ch13_navigation_reuse','navigation.launch.py','repo_root:='+str(root),'report:='+str(out/'engine.json'),'scene:='+scene,'vision_inference_hz:='+str(args.vision_hz),'manipulation:='+('true' if handoff is not None else 'false'),'planning:='+('true' if planning else 'false'),'pick_scene:='+('true' if pick_scene else 'false'),'max_sim_s:='+('360' if planning else '120')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  rclpy.init();node=Node('ch13_reuse_navigation_probe');action=ActionClient(node,NavigateToPose,'/navigate_to_pose')
  def on_clock(m):
   nonlocal clock_ns
   clock_ns=ns(m.clock)
  def on_state(m):
   nonlocal state
   state=m;poses.append({'stamp_ns':ns(m.header.stamp),'wall':time.monotonic(),'x':m.pose.pose.position.x,'y':m.pose.pose.position.y,'yaw':yaw(m.pose.pose.orientation)})
  def status(name,m):
   nonlocal gateway,platform,boundary
   value=json.loads(m.data)
   if name=='gateway':gateway=value
   elif name=='platform':platform=value
   else:boundary=value
  def on_observation(m):
   nonlocal observation
   observation=json.loads(m.data)
  def on_joints(m):
   nonlocal joints
   joints=m
  def on_grid(m):
   nonlocal grid
   grid={'width':m.info.width,'height':m.info.height,'resolution':m.info.resolution,'origin':[m.info.origin.position.x,m.info.origin.position.y],'data':list(m.data)}
  def on_vision_status(m):
   nonlocal vision_status
   vision_status=json.loads(m.data)
  node.create_subscription(String,N+'/vision/observation',on_observation,1);node.create_subscription(String,N+'/vision/status',on_vision_status,1);node.create_subscription(JointState,N+'/joint_states',on_joints,1);node.create_subscription(OccupancyGrid,N+'/map',on_grid,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
  node.create_subscription(Clock,'/clock',on_clock,1);node.create_subscription(Odometry,N+'/engine_state',on_state,1)
  for name in ['gateway','platform','navigation']:node.create_subscription(String,N+'/'+name+'/status',lambda m,n=name:status(n,m),1)
  node.create_subscription(NavPath,'/plan',lambda m:plans.append([[p.pose.position.x,p.pose.position.y] for p in m.poses]),1)
  def until(predicate,timeout):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    rclpy.spin_once(node,timeout_sec=.01)
    if predicate():return True
    if launch.poll() is not None:raise RuntimeError('owned launch exited: '+str(launch.returncode))
   return False
  def call(name,timeout=3):return service_call(node,N+'/'+name,Trigger.Request(),until,clients,timeout=timeout)
  original_call=call
  if startup_only:
   from ch13_navigation_reuse.startup_trace import require_startup_service
   S.update(startup_only=True,startup_service_calls=[])
   def call(name,timeout=3):
    require_startup_service(name);S['startup_service_calls'].append(name)
    return original_call(name,timeout)
  def stop_owned_planner():
   if not planning or S.get('planner_stopped_before_engine'):return
   text=(out/'launch.log').read_text();owned=[int(p) for p in re.findall(r'process started with pid \[(\d+)\]',text)]
   planners=[]
   for pid in owned:
    proc=Path('/proc')/str(pid)
    if not (proc/'cmdline').exists():continue
    command=(proc/'cmdline').read_bytes().split(b'\0')
    if command and command[0].endswith(b'/ch13_manipulation_planner/planner_runtime'):
     assert int((proc/'stat').read_text().split(') ',1)[1].split()[1])==launch.pid,'planner parent ownership mismatch'
     planners.append(pid)
   assert len(planners)<=1,'duplicate owned planner'
   if planners:
    response=call('manipulation/planner/shutdown');assert response.success,response.message
   assert until(lambda:all(not (Path('/proc')/str(p)/'cmdline').exists() for p in planners),8.),'planner did not exit while engine clock remained live'
   S['planner_stopped_before_engine']=True;S['planner_stop_clock_ns']=clock_ns
  def startup_ready():return state is not None and clock_ns>2_000_000_000 and gateway.get('ready_for_arm') and boundary.get('frames_ready') and boundary.get('pending_future_count',0)==0 and platform.get('counts',{}).get('safe')==1 and platform.get('stationary_ready') and action.server_is_ready()
  def startup_fault():return bool(gateway.get('fault') or boundary.get('fault') or platform.get('fault'))
  if startup_only:
   assert until(lambda:startup_ready() or startup_fault(),35),'startup readiness deadline'
   assert not startup_fault(),'startup fault before admission'
   assert startup_ready()
   until(startup_fault,1.)
   assert not startup_fault(),'startup fault during disarmed observation'
   assert gateway.get('mode')==platform.get('mode')=='DISARMED'
   assert goal_handle is None and result_future is None and not S['events']
   response=call('platform/shutdown');assert response.success,response.message
   launch.wait(timeout=12);assert launch.returncode==0
   S['engine']=json.loads((out/'engine.json').read_text());S['result']='PASS'
   raise _StartupComplete()
  assert until(startup_ready,35),'startup/Nav2 readiness deadline'
  for name in ['planner_server','controller_server','velocity_smoother','bt_navigator']:
   end=time.monotonic()+8.
   while True:
    response=service_call(node,'/'+name+'/get_state',GetState.Request(),until,clients,GetState,timeout=3.)
    if response.current_state.id==3:break
    assert time.monotonic()<end,'Nav2 lifecycle not ACTIVE: '+name
    until(lambda:False,.1)
  for name in ['navigation/enable','navigation/require_vision','navigation/release','navigation/idle','platform/arm','gateway/arm','platform/shutdown']:
   full=N+'/'+name;client=node.create_client(Trigger,full);clients[full]=client;assert until(client.service_is_ready,3),'missing admission service '+full
  target=[.65,0.,0.]
  if args.case=='obstacle':target=[2.25,0.,0.]
  if args.case=='blocked':target=[2.25,0.,0.]
  if args.case in ['cancel','raw_loss']:target=[2.5,0.,0.]
  if args.case=='vision':
   from vision_mission import select_goal
   target,vision_record,arm_model=select_goal(root,node,until,lambda:observation,lambda:state,lambda:joints,lambda:grid,lambda:clock_ns);S['vision_admission']=vision_record
   required_capture=vision_record['source_observation']['capture_ns'];assert until(lambda:boundary.get('vision_capture_ns',0)>=required_capture and boundary.get('vision_capture_age_wall_s',1.)<=.3,2),'navigation boundary has not received the same fresh capture'
   response=call('navigation/require_vision');assert response.success,response.message

  S['target']=target;start_xy=[state.pose.pose.position.x,state.pose.pose.position.y];start_sim=clock_ns;start_wall=time.monotonic();response=call('navigation/enable');assert response.success,response.message
  goal=NavigateToPose.Goal();goal.pose.header.frame_id='reuse/map';set_stamp(goal.pose.header.stamp,vision_record['source_observation']['capture_ns'] if vision_record is not None else clock_ns);goal.pose.pose.position.x=target[0];goal.pose.pose.position.y=target[1];goal.pose.pose.orientation.z=math.sin(target[2]/2);goal.pose.pose.orientation.w=math.cos(target[2]/2)
  S['goal_header_stamp_ns']=ns(goal.pose.header.stamp)
  sent=action.send_goal_async(goal);assert until(sent.done,5),'goal admission deadline';goal_handle=sent.result();assert goal_handle.accepted,'Nav2 goal rejected';result_future=goal_handle.get_result_async();S['events'].append({'event':'goal_accepted','sim_ns':clock_ns,'wall':time.monotonic()})
  assert until(lambda:result_future.done() or boundary.get('phase')=='FAULT' or (boundary.get('phase')=='ACTIVE' and boundary.get('output_held') and gateway.get('ready_for_arm')),5),'controller preparation deadline'
  if not result_future.done():
   assert boundary.get('phase')=='ACTIVE' and boundary.get('output_held') and gateway.get('ready_for_arm'),'controller not prepared at zero'
   S['motion_admission']={'boundary_phase':boundary['phase'],'held':boundary['output_held'],'gateway_before':gateway['mode'],'controller_stamp_ns':boundary['stamp_ns']}
   response=call('gateway/arm');assert response.success,response.message;S['motion_admission']['gateway_arm_wall']=time.monotonic()
   response=call('platform/arm');assert response.success,response.message;S['motion_admission']['platform_arm_wall']=time.monotonic()
   response=call('navigation/release');assert response.success,response.message;S['motion_admission']['release_wall']=time.monotonic();S['motion_release_sim_ns']=clock_ns
  else:S['motion_not_released_terminal']=result_future.result().status
  if args.case in ['cancel','raw_loss']:
   assert until(lambda:clock_ns-S['motion_release_sim_ns']>=2_000_000_000 and boundary.get('phase')=='ACTIVE' and not platform.get('fault') and math.hypot(state.pose.pose.position.x-start_xy[0],state.pose.pose.position.y-start_xy[1])>.03,12),'no active movement before injection'
   if args.case=='raw_loss':
    text=(out/'launch.log').read_text();owned=[int(x) for x in re.findall(r'process started with pid \[(\d+)\]',text)];victims=[]
    for pid in owned:
     cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0') if (Path('/proc')/str(pid)/'cmdline').exists() else []
     if b'ch13_navigation_reuse.navigation_boundary' in cmd:
      assert int((Path('/proc')/str(pid)/'stat').read_text().split(') ',1)[1].split()[1])==launch.pid,'boundary parent ownership mismatch'
      victims.append(pid)
    assert len(victims)==1,'owned boundary identity';paused_pid=victims[0]
    S['raw_loss_injection']=dict(request_wall=time.monotonic(),sim_ns=clock_ns,
        gateway_mode=gateway.get('mode'),gateway_fault=gateway.get('fault'),
        platform_mode=platform.get('mode'),platform_fault=platform.get('fault'))
    os.kill(paused_pid,signal.SIGSTOP);S['raw_loss_injection']['pause_sent_wall']=time.monotonic()
    S['injected_boundary_pid']=paused_pid;S['injection']='owned_publisher_pause_with_identity_preserved'
    assert until(lambda:gateway.get('mode')=='FAULT',2),'raw loss did not latch';receipt=gateway['source_receipts']['raw']['receipt_wall'];S['raw_expiry_decision_latency_s']=gateway['decision_wall']-receipt;assert S['raw_expiry_decision_latency_s']<=.35
    os.kill(paused_pid,signal.SIGCONT);paused_pid=None;until(lambda:False,.2);assert gateway.get('mode')=='FAULT';S['no_auto_resume_after_raw_return']=True
   canceled=goal_handle.cancel_goal_async();assert until(canceled.done,3),'cancel ACK deadline';S['cancel_ack']=bool(canceled.result().goals_canceling);assert S['cancel_ack']
  if args.case not in ['cancel','raw_loss']:
   assert until(lambda:result_future.done() or boundary.get('phase')=='FAULT' or gateway.get('mode')=='FAULT' or bool(platform.get('fault')),240),'NavigateToPose terminal deadline'
   if not result_future.done():
    S['safety_fault_before_terminal']={'boundary':boundary.get('fault'),'gateway':gateway.get('fault'),'platform':platform.get('fault')};canceled=goal_handle.cancel_goal_async();assert until(canceled.done,3);assert until(result_future.done,3),'terminal missing after safety cancellation'
  assert until(result_future.done,3),'NavigateToPose terminal deadline';terminal=result_future.result();S['terminal_status']=terminal.status;S['terminal_sim_ns']=clock_ns
  expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
  assert clock_ns-start_sim<=90_000_000_000,'navigation sim budget'
  if args.case!='raw_loss':response=call('navigation/idle');assert response.success,response.message
  zero_wall=time.monotonic();zero_sim=clock_ns;assert until(lambda:platform.get('stationary_ready'),8),'terminal received but physical stop not settled';assert clock_ns-zero_sim<=5_000_000_000
  S['terminal_to_settled_wall_s']=time.monotonic()-zero_wall;S['displacement_m']=math.hypot(state.pose.pose.position.x-start_xy[0],state.pose.pose.position.y-start_xy[1]);S['actual_goal_error_m']=math.hypot(state.pose.pose.position.x-target[0],state.pose.pose.position.y-target[1]);S['actual_goal_yaw_error_rad']=abs(math.atan2(math.sin(yaw(state.pose.pose.orientation)-target[2]),math.cos(yaw(state.pose.pose.orientation)-target[2])))
  if expected==4:assert S['actual_goal_error_m']<=.10 and S['actual_goal_yaw_error_rad']<=.10
  if args.case=='obstacle':assert max(abs(p['y']) for p in poses)>.45,'no measured obstacle bypass'
  if args.case=='raw_loss':assert gateway['mode']=='FAULT'
  if args.case=='vision':
   from vision_mission import current_q
   from ch13_navigation_reuse.approach_geometry import position_ik
   from ch13_navigation_reuse.vision_geometry import admissible,manipulation_ready
   assert until(lambda:observation is not None and admissible(observation['capture_ns'],observation['capture_wall'],clock_ns,time.monotonic(),observation['tf_stamp_ns']),2),'no fresh final observation'
   final_observation=observation;reach=position_ik(arm_model,current_q(state,joints),final_observation['point']);S['final_arm_workspace']=reach
   valid_observation=reach is not None and admissible(final_observation['capture_ns'],final_observation['capture_wall'],clock_ns,time.monotonic(),final_observation['tf_stamp_ns'])
   ready=manipulation_ready(terminal.status,S['actual_goal_error_m'],S['actual_goal_yaw_error_rad'],platform.get('stationary_ready'),valid_observation,bool(gateway.get('fault') or boundary.get('fault') or vision_status.get('fault')));assert ready,'terminal/pose/stop/observation/workspace not ready'
   ready_pub=node.create_publisher(String,N+'/ready_for_manipulation',1);payload={'state':'READY_FOR_MANIPULATION','terminal':terminal.status,'actual_position_error_m':S['actual_goal_error_m'],'actual_yaw_error_rad':S['actual_goal_yaw_error_rad'],'capture_ns':final_observation['capture_ns'],'workspace':reach,'stamp_ns':clock_ns,'capture_wall':final_observation['capture_wall'],'decision_wall':time.monotonic(),'tf_stamp_ns':final_observation['tf_stamp_ns']};ready_pub.publish(String(data=json.dumps(payload)));S['ready_for_manipulation']=payload
   if handoff is not None:
    S['manipulation_handoff']=handoff(node=node,until=until,call=call,out=out,
      goal_id=bytes(goal_handle.goal_id.uuid).hex(),target=list(target),
      snapshot=lambda:{'observation':observation,'state':state,'joints':joints,'clock_ns':clock_ns,'platform':platform,'boundary':boundary,'gateway':gateway})
    assert not gateway.get('fault') and not boundary.get('fault') and not platform.get('fault'),('fault during manipulation',gateway,boundary,platform)
   else:until(lambda:False,.15)
   ready_pub.publish(String(data=json.dumps({'state':'NOT_READY','reason':'normal_shutdown','stamp_ns':clock_ns})))
  stop_owned_planner()
  S['plan_count']=len(plans);S['max_abs_y_m']=max(abs(p['y']) for p in poses);response=call('platform/shutdown');assert response.success,response.message;launch.wait(timeout=12);assert launch.returncode==0;S['engine']=json.loads((out/'engine.json').read_text());assert S['engine']['normal_shutdown_requested'] and S['engine']['rx_joined'] and S['engine']['upstream_threads_joined'];S['result']='PASS'
 except _StartupComplete:pass
 except BaseException:S['error']=traceback.format_exc()
 finally:
  if paused_pid is not None:
   try:os.kill(paused_pid,signal.SIGCONT)
   except ProcessLookupError:pass
  S['gateway_last']=gateway;S['platform_last']=platform;S['navigation_last']=boundary;S['vision_last']=vision_status
  if node is not None and launch is not None and launch.poll() is None:
   try:
    try:stop_owned_planner()
    except BaseException:S['planner_cleanup_error']=traceback.format_exc()
    if goal_handle is not None and result_future is not None and not result_future.done():goal_handle.cancel_goal_async()
    service_call(node,N+'/navigation/idle',Trigger.Request(),until,clients,timeout=1.)
    if until(lambda:platform.get('stationary_ready'),8):service_call(node,N+'/platform/shutdown',Trigger.Request(),until,clients,timeout=2.);launch.wait(timeout=12)
   except BaseException:S['cleanup_error']=traceback.format_exc()
  if node is not None:node.destroy_node();rclpy.try_shutdown()
  if launch is not None and launch.poll() is None:
   launch.send_signal(signal.SIGINT)
   try:launch.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(launch.pid,signal.SIGKILL);launch.wait(timeout=3)
  if log is not None:log.close()
  if (out/'launch.log').exists():
   text=(out/'launch.log').read_text();pids=re.findall(r'process started with pid \[(\d+)\]',text);S['owned_launch_pids']=list(map(int,pids));S['remaining_launch_pids']=[int(p) for p in pids if (Path('/proc')/p/'cmdline').exists()];S['clean_launch_exits']=text.count('process has finished cleanly');S['launch_exit_code']=None if launch is None else launch.returncode
   if S['result']=='PASS' and (S['remaining_launch_pids'] or S['clean_launch_exits']!=len(pids) or 'process has died' in text):S['result']='FAIL';S['error']='launch child lifecycle failure'
  (out/'ros_poses.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in poses));(out/'plans.json').write_text(json.dumps(plans));(out/'navigation_summary.json').write_text(json.dumps(S,indent=2)+'\n');print(json.dumps(S,indent=2),flush=True)
 return 0 if S['result']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
