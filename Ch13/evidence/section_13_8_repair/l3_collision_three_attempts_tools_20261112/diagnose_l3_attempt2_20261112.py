"""Post-exit saved-state MoveIt IK/collision probe. No engine or actuator goal."""
import fcntl,hashlib,json,os,signal,subprocess,sys,time,tarfile
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='136'
import numpy as np,mujoco,rclpy,yaml
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import Transform,PoseStamped
from moveit_msgs.msg import RobotState,LinkPadding,Constraints,PositionConstraint,OrientationConstraint,JointConstraint
from moveit_msgs.srv import GetPositionIK,GetStateValidity,ApplyPlanningScene,GetMotionPlan
from std_srvs.srv import Trigger
from ament_index_python.packages import get_package_prefix
from ch13_piper_moveit_config.configuration import parameters
from ch13_manipulation_reuse.planning import pose,object_box,object_cylinder
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.model import urdf_fk
from ch13_manipulation_reuse.trajectory import JOINTS
from ch13_navigation_reuse.scene import layout
from ch13_system_validation.scenarios import get_scenario,grasp_pose
from ch13_system_validation.worlds import planning_objects

root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=False,parents=True)
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level3_house'
scenario=get_scenario('level3_house');config=parameters();config['use_sim_time']=False;config['ompl']['path_tolerance']=.001;config['ompl']['manipulator_arm']['longest_valid_segment_fraction']=.0001
(out/'planner.yaml').write_text(yaml.safe_dump({'reuse_move_group':{'ros__parameters':config}}))
model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
ids=['ddd74629-0abb-42ed-bc47-568e857b5d59','d382c578-4e5f-4f82-945b-d33d113eb06f','4b413caf-5b0e-43af-93ca-04e4d1058431','29b1f378-bed4-4fcb-8849-2f9e3d55f00a']
report=dict(scope='saved actual states, installed MoveIt IK/validity; no engine or command authority',rows=[],contacts_v29=[],robot_description_sha256=hashlib.sha256(config['robot_description'].encode()).hexdigest())
lock=(root.parent/'ch13_reuse_engine.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
process=None;node=None
try:
 rclpy.init();node=rclpy.create_node('saved_level3_ik_diagnostic')
 clients={name:node.create_client(typ,name) for name,typ in [('/plan_kinematic_path',GetMotionPlan),('/compute_ik',GetPositionIK),('/check_state_validity',GetStateValidity),('/apply_planning_scene',ApplyPlanningScene),('/ch13/reuse/manipulation/planner/shutdown',Trigger)]}
 assert not clients['/compute_ik'].service_is_ready(),'another planner in diagnostic domain'
 binary=Path(get_package_prefix('ch13_manipulation_planner'))/'lib/ch13_manipulation_planner/planner_runtime'
 process=subprocess.Popen([str(binary),'--ros-args','--params-file',str(out/'planner.yaml')],stdout=(out/'planner.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 def until(predicate,seconds):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   rclpy.spin_once(node,timeout_sec=.01)
   if predicate():return True
   if process.poll() is not None:raise RuntimeError('diagnostic planner exited')
  return False
 def call(name,request,seconds=5.):
  f=clients[name].call_async(request);assert until(f.done,seconds),name;return f.result()
 assert until(lambda:all(c.service_is_ready() for c in clients.values()),30.)
 def state(q):
  s=RobotState();s.is_diff=False
  for j in range(model.njnt):
   if model.jnt_type[j]==mujoco.mjtJoint.mjJNT_FREE:continue
   s.joint_state.name.append(model.joint(j).name);s.joint_state.position.append(float(q[model.jnt_qposadr[j]]))
  s.multi_dof_joint_state.header.frame_id='reuse/odom'
  s.multi_dof_joint_state.joint_names=['world_joint'];t=Transform()
  t.translation.x,t.translation.y,t.translation.z=map(float,q[:3]);t.rotation.w,t.rotation.x,t.rotation.y,t.rotation.z=map(float,q[3:7]);s.multi_dof_joint_state.transforms=[t]
  return s
 case=root/'Ch13/evidence/section_13_8_system/e475ece0-9f70-4dae-8de9-491ee92c95fc'
 raw_manifest=json.loads((case/'raw_manifest.json').read_text())
 archive=case/'raw.tar.gz'
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==raw_manifest['archive_sha256']
 def read_saved(name):
  with tarfile.open(archive,'r:gz') as tar:data=tar.extractfile(name).read()
  expected=next(r['sha256'] for r in raw_manifest['files'] if r['path']==name)
  assert hashlib.sha256(data).hexdigest()==expected,name
  return data.decode()
 samples=[json.loads(line) for line in read_saved('engine_observations.jsonl').splitlines()]
 ns=next(r['clock_ns'] for r in json.loads(read_saved('pick_mission.json'))['stages'] if r.get('phase')=='PRE_GRASP')
 anchor=min(samples,key=lambda r:abs(r['sim_s']-ns/1e9));last=samples[-1]
 valid=[json.loads(line) for line in read_saved('vision_observations.jsonl').splitlines()];valid=[r for r in valid if 'point' in r and r.get('capture_ns',0)<=ns]
 observation=max(valid,key=lambda r:r['capture_ns']);center=np.array(observation['point'])
 apply=ApplyPlanningScene.Request();apply.scene.is_diff=True;apply.scene.robot_state.is_diff=True
 apply.scene.world.collision_objects=[object_box('ground',[0,0,-.01],[20,20,.02])]+[object_box('reuse_'+n,c,2*np.array(z)) for n,c,z in layout('vision') if n!='target']+planning_objects(scenario)+[object_cylinder('pick_target',center)]
 assert call('/apply_planning_scene',apply).success
 change=ApplyPlanningScene.Request();change.scene.is_diff=True;change.scene.robot_state.is_diff=True
 change.scene.link_padding=[LinkPadding(link_name='reuse/link3',padding=.03)]
 assert call('/apply_planning_scene',change).success
 report['link3_world_padding_m']=.03
 aq=np.array(anchor['qpos']);forward=center-np.array([*aq[:2],center[2]]);forward/=np.linalg.norm(forward)
 pre,rot=grasp_pose(center,forward,-1.,scenario)
 plans=json.loads(read_saved('pick_mission.json'))['planning']
 report['case']=case.name;report['anchor_sim_s']=anchor['sim_s'];report['center']=center.tolist()
 for padding in (.03,):
  change.scene.link_padding=[LinkPadding(link_name='reuse/link3',padding=padding)]
  assert call('/apply_planning_scene',change).success
  for index,plan in enumerate(r for r in plans if r.get('kind')=='plan'):
   trajectory=plan['trajectory']['joint_trajectory'];points=trajectory['points'];checks=[]
   for i in sorted(set([0,len(points)-1,*({0:[538,539,540,541],1:[388,389,390,391,392,967,1013,1014,1015,1016,1017,1018,1019,1020,1021]}[index])])):
    q=aq.copy()
    for name,value in zip(trajectory['joint_names'],points[i]['positions']):q[model.jnt_qposadr[model.joint(name).id]]=value
    req=GetStateValidity.Request();req.robot_state=state(q);req.group_name='manipulator_arm';v=call('/check_state_validity',req)
    checks.append(dict(index=i,valid=v.valid,contacts=[dict(first=c.contact_body_1,second=c.contact_body_2,depth=c.depth) for c in v.contacts]))
   report['rows'].append(dict(padding=padding,candidate=index,point_count=len(points),checks=checks))
 from shape_msgs.msg import SolidPrimitive
 from rosidl_runtime_py.convert import message_to_ordereddict
 from ch13_manipulation_reuse.retime import normalize_points
 report['attempt']=2;report['fraction']=.0001;report['replanned']=[]
 for sign in (1.,-1.):
  request=GetMotionPlan.Request();motion=request.motion_plan_request
  motion.group_name='manipulator_arm';motion.pipeline_id='ompl';motion.planner_id='RRTConnectkConfigDefault'
  motion.num_planning_attempts=1;motion.allowed_planning_time=2.
  motion.max_velocity_scaling_factor=.08;motion.max_acceleration_scaling_factor=.08;motion.start_state=state(aq)
  motion.workspace_parameters.header.frame_id='reuse/odom'
  motion.workspace_parameters.min_corner.x=motion.workspace_parameters.min_corner.y=-5.;motion.workspace_parameters.min_corner.z=-1.
  motion.workspace_parameters.max_corner.x=motion.workspace_parameters.max_corner.y=5.;motion.workspace_parameters.max_corner.z=3.
  pre,rotation=grasp_pose(center,forward,sign,scenario)
  constraint=Constraints();position=PositionConstraint();position.header.frame_id='reuse/odom';position.link_name='reuse/tcp'
  position.constraint_region.primitives=[SolidPrimitive(type=SolidPrimitive.SPHERE,dimensions=[.001])]
  position.constraint_region.primitive_poses=[pose(pre,rotation)];position.weight=1.
  orientation=OrientationConstraint();orientation.header.frame_id='reuse/odom';orientation.link_name='reuse/tcp'
  orientation.orientation=pose(pre,rotation).orientation
  orientation.absolute_x_axis_tolerance=orientation.absolute_y_axis_tolerance=orientation.absolute_z_axis_tolerance=.01;orientation.weight=1.
  ik_request=GetPositionIK.Request();ik=ik_request.ik_request
  ik.group_name='manipulator_arm';ik.ik_link_name='reuse/tcp';ik.avoid_collisions=True;ik.robot_state=state(aq)
  ik.pose_stamped.header.frame_id='reuse/odom';ik.pose_stamped.pose=pose(pre,rotation);ik.timeout.sec=1
  solved=call('/compute_ik',ik_request)
  if solved.error_code.val!=1:
   report['replanned'].append(dict(sign=sign,ik_error_code=solved.error_code.val));continue
  goal_joints=dict(zip(solved.solution.joint_state.name,solved.solution.joint_state.position))
  validity=GetStateValidity.Request();validity.robot_state=solved.solution;validity.group_name='manipulator_arm'
  checked=call('/check_state_validity',validity)
  assert checked.valid,'collision-aware IK returned invalid endpoint'
  constraint=Constraints()
  for name in JOINTS:
   constraint.joint_constraints.append(JointConstraint(joint_name=name,position=goal_joints[name],tolerance_above=.001,tolerance_below=.001,weight=1.))
  motion.goal_constraints=[constraint]
  response=call('/plan_kinematic_path',request,12.).motion_plan_response
  entry=dict(sign=sign,error_code=response.error_code.val,planning_time=response.planning_time,trajectory=message_to_ordereddict(response.trajectory))
  if response.error_code.val==1:
   trajectory=response.trajectory.joint_trajectory
   points=[dict(time=p.time_from_start.sec+p.time_from_start.nanosec/1e9,positions=list(p.positions),velocities=list(p.velocities),accelerations=list(p.accelerations)) for p in trajectory.points]
   initial=[float(aq[model.jnt_qposadr[model.joint(name).id]]) for name in trajectory.joint_names]
   try:
    normalized,scale=normalize_points(tuple(trajectory.joint_names),points,initial,[[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]],refine_scale=True)
    entry.update(execution_admission=True,execution_duration_sim_s=normalized[-1]['time'],scale=scale)
   except ValueError as error:entry.update(execution_admission=False,execution_rejection=str(error))
  report['replanned'].append(entry)
 report['attempt_pass']=any(r.get('execution_admission') for r in report['replanned'])
 response=call('/ch13/reuse/manipulation/planner/shutdown',Trigger.Request());report['shutdown_ack']=response.success;process.wait(timeout=8.);report['planner_exit']=process.returncode
finally:
 if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
 if node is not None:node.destroy_node();rclpy.try_shutdown()
 lock.close();(out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(case=report.get('case'),rows=[dict(padding=r['padding'],candidate=r['candidate'],invalid=[v for v in r['checks'] if not v['valid']]) for r in report['rows']],shutdown=report.get('shutdown_ack'),exit=report.get('planner_exit'))))
