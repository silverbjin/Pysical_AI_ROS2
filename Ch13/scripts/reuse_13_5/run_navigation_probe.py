"""Owned Nav2+MuJoCo probe. Action terminals and measured stop are separate."""
import argparse,json,math,os,re,signal,subprocess,sys,time,traceback
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import Odometry,Path as NavPath
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from std_srvs.srv import Trigger
from ch13_navigation_reuse.command_gateway import N,ns,set_stamp
from run_r2_probe import service_call

def yaw(q):return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--evidence',required=True);ap.add_argument('--case',choices=['free','obstacle','blocked','cancel','raw_loss','vision'],default='free');args=ap.parse_args()
 root=Path(args.repo_root);out=Path(args.evidence);out.mkdir(parents=True,exist_ok=True);scene=args.case if args.case in ['obstacle','blocked','vision'] else 'free'
 S={'result':'FAIL','case':args.case,'events':[]};node=None;launch=None;log=None;goal_handle=None;result_future=None;clock_ns=0;state=None;gateway={};platform={};boundary={};poses=[];plans=[];clients={}
 try:
  (out/'boot_id.txt').write_text(Path('/proc/sys/kernel/random/boot_id').read_text());log=(out/'launch.log').open('w')
  launch=subprocess.Popen(['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch','ch13_navigation_reuse','navigation.launch.py','repo_root:='+str(root),'report:='+str(out/'engine.json'),'scene:='+scene],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
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
  assert until(lambda:state is not None and clock_ns>2_000_000_000 and gateway.get('ready_for_arm') and boundary.get('frames_ready') and platform.get('counts',{}).get('safe')==1 and platform.get('stationary_ready') and action.server_is_ready(),35),'startup/Nav2 readiness deadline'
  for name in ['planner_server','controller_server','velocity_smoother','bt_navigator']:
   end=time.monotonic()+8.
   while True:
    response=service_call(node,'/'+name+'/get_state',GetState.Request(),until,clients,GetState,timeout=3.)
    if response.current_state.id==3:break
    assert time.monotonic()<end,'Nav2 lifecycle not ACTIVE: '+name
    until(lambda:False,.1)
  for name in ['platform/arm','gateway/arm']:response=call(name);assert response.success,response.message
  target=[.65,0.,0.]
  if args.case=='obstacle':target=[2.25,0.,0.]
  if args.case=='blocked':target=[1.2,0.,0.]
  if args.case in ['cancel','raw_loss']:target=[2.5,0.,0.]
  if args.case=='vision':raise RuntimeError('vision admission not connected yet')
  S['target']=target;start_xy=[state.pose.pose.position.x,state.pose.pose.position.y];start_sim=clock_ns;start_wall=time.monotonic();response=call('navigation/enable');assert response.success,response.message
  goal=NavigateToPose.Goal();goal.pose.header.frame_id='reuse/map';set_stamp(goal.pose.header.stamp,clock_ns);goal.pose.pose.position.x=target[0];goal.pose.pose.position.y=target[1];goal.pose.pose.orientation.z=math.sin(target[2]/2);goal.pose.pose.orientation.w=math.cos(target[2]/2)
  sent=action.send_goal_async(goal);assert until(sent.done,5),'goal admission deadline';goal_handle=sent.result();assert goal_handle.accepted,'Nav2 goal rejected';result_future=goal_handle.get_result_async();S['events'].append({'event':'goal_accepted','sim_ns':clock_ns,'wall':time.monotonic()})
  if args.case in ['cancel','raw_loss']:
   assert until(lambda:clock_ns-start_sim>=2_000_000_000 and boundary.get('phase')=='ACTIVE',12),'no active movement before injection'
   if args.case=='raw_loss':
    text=(out/'launch.log').read_text();owned=[int(x) for x in re.findall(r'process started with pid \[(\d+)\]',text)];victims=[]
    for pid in owned:
     cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0') if (Path('/proc')/str(pid)/'cmdline').exists() else []
     if b'ch13_navigation_reuse.navigation_boundary' in cmd:victims.append(pid)
    assert len(victims)==1,'owned boundary identity';os.kill(victims[0],signal.SIGTERM);S['injected_boundary_pid']=victims[0]
    assert until(lambda:gateway.get('mode')=='FAULT',2),'raw loss did not latch';receipt=gateway['source_receipts']['raw']['receipt_wall'];S['raw_expiry_decision_latency_s']=gateway['decision_wall']-receipt;assert S['raw_expiry_decision_latency_s']<=.35
   canceled=goal_handle.cancel_goal_async();assert until(canceled.done,3),'cancel ACK deadline';S['cancel_ack']=bool(canceled.result().goals_canceling);assert S['cancel_ack']
  assert until(result_future.done,240),'NavigateToPose terminal deadline';terminal=result_future.result();S['terminal_status']=terminal.status;S['terminal_sim_ns']=clock_ns
  expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
  assert clock_ns-start_sim<=90_000_000_000,'navigation sim budget'
  if args.case!='raw_loss':response=call('navigation/idle');assert response.success,response.message
  zero_wall=time.monotonic();zero_sim=clock_ns;assert until(lambda:platform.get('stationary_ready'),8),'terminal received but physical stop not settled';assert clock_ns-zero_sim<=5_000_000_000
  S['terminal_to_settled_wall_s']=time.monotonic()-zero_wall;S['displacement_m']=math.hypot(state.pose.pose.position.x-start_xy[0],state.pose.pose.position.y-start_xy[1]);S['actual_goal_error_m']=math.hypot(state.pose.pose.position.x-target[0],state.pose.pose.position.y-target[1]);S['actual_goal_yaw_error_rad']=abs(math.atan2(math.sin(yaw(state.pose.pose.orientation)-target[2]),math.cos(yaw(state.pose.pose.orientation)-target[2])))
  if expected==4:assert S['actual_goal_error_m']<=.10 and S['actual_goal_yaw_error_rad']<=.10
  if args.case=='obstacle':assert max(abs(p['y']) for p in poses)>.45,'no measured obstacle bypass'
  if args.case=='raw_loss':assert gateway['mode']=='FAULT'
  S['plan_count']=len(plans);S['max_abs_y_m']=max(abs(p['y']) for p in poses);response=call('platform/shutdown');assert response.success,response.message;launch.wait(timeout=12);assert launch.returncode==0;S['engine']=json.loads((out/'engine.json').read_text());assert S['engine']['normal_shutdown_requested'] and S['engine']['rx_joined'] and S['engine']['upstream_threads_joined'];S['result']='PASS'
 except BaseException:S['error']=traceback.format_exc()
 finally:
  S['gateway_last']=gateway;S['platform_last']=platform;S['navigation_last']=boundary
  if node is not None and launch is not None and launch.poll() is None:
   try:
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
