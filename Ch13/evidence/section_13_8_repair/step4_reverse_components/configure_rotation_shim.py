"""Installed controller configure only; no simulator, action goal or actuator."""
import fcntl,json,os,signal,subprocess,sys,time
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='137'
import rclpy,yaml
from lifecycle_msgs.srv import ChangeState
from rcl_interfaces.srv import GetParameters
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False)
params=yaml.safe_load((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/nav2_params.yaml').read_text())
def clock_off(value):
 if isinstance(value,dict):
  for key,child in value.items():
   if key=='use_sim_time':value[key]=False
   else:clock_off(child)
clock_off(params)
c=params['controller_server']['ros__parameters'];p=c['FollowPath']
p.update(plugin='nav2_rotation_shim_controller::RotationShimController',primary_controller='nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController',use_rotate_to_heading=False,allow_reversing=True,rotate_to_goal_heading=True,use_path_orientations=True,rotate_to_heading_once=True,stateful=False)
c['FollowPath.position_checker.stateful']=False
if sys.argv[3]=='green':c['.position_checker.stateful']=False
(out/'controller.yaml').write_text(yaml.safe_dump(params))
report=dict(scope='installed shim/RPP configure only; no engine or actuator command',result='ERROR')
lock=(root.parent/'ch13_reuse_engine.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
rclpy.init();node=rclpy.create_node('shim_configuration_diagnostic');process=None
try:
 life=node.create_client(ChangeState,'/controller_server/change_state');assert not life.service_is_ready(),'foreign controller'
 process=subprocess.Popen(['/opt/ros/jazzy/lib/nav2_controller/controller_server','--ros-args','--params-file',str(out/'controller.yaml')],stdout=(out/'controller.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 def until(predicate,seconds):
  deadline=time.monotonic()+seconds
  while time.monotonic()<deadline:
   rclpy.spin_once(node,timeout_sec=.01)
   if predicate():return True
   assert process.poll() is None,'owned controller exited'
  return False
 assert until(life.service_is_ready,15.)
 def transition(value):
  req=ChangeState.Request();req.transition.id=value;future=life.call_async(req)
  assert until(future.done,10.);return future.result().success
 report['configured']=transition(1);assert report['configured']
 get=node.create_client(GetParameters,'/controller_server/get_parameters');assert until(get.service_is_ready,3.)
 names=['FollowPath.plugin','FollowPath.primary_controller','FollowPath.allow_reversing','FollowPath.use_rotate_to_heading','FollowPath.rotate_to_goal_heading','FollowPath.use_path_orientations','.position_checker.stateful','FollowPath.rotate_to_heading_angular_vel','FollowPath.max_angular_accel']
 req=GetParameters.Request();req.names=names;future=get.call_async(req);assert until(future.done,3.)
 report['parameters']={name:dict(type=v.type,bool=v.bool_value,string=v.string_value,double=v.double_value) for name,v in zip(names,future.result().values)}
 report['cleaned']=transition(2);process.send_signal(signal.SIGINT);process.wait(timeout=8.);report['exit_code']=process.returncode
 report['result']='PASS' if report['parameters']['.position_checker.stateful']['bool'] is False else 'FAIL'
finally:
 if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
 node.destroy_node();rclpy.try_shutdown();lock.close();(out/'configuration.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));sys.exit(0 if report['result']=='PASS' else 1)
