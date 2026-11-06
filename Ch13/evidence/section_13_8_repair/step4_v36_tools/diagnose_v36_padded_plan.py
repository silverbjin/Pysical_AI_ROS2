"""Post-exit saved-state MoveIt IK/collision probe. No engine or actuator goal."""
import fcntl,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='136'
import numpy as np,mujoco,rclpy,yaml
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import Transform
from moveit_msgs.msg import RobotState,LinkPadding,Constraints,JointConstraint
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
scenario=get_scenario('level3_house');config=parameters();config['use_sim_time']=False
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
 case=root/'Ch13/evidence/section_13_8_system/d0611273-5f74-47a8-b108-12d189dbd523'
 samples=[json.loads(line) for line in (case/'engine_observations.jsonl').open()]
 ns=next(r['clock_ns'] for r in json.loads((case/'pick_mission.json').read_text())['stages'] if r.get('phase')=='PRE_GRASP')
 anchor=min(samples,key=lambda r:abs(r['sim_s']-ns/1e9));last=samples[-1]
 valid=[json.loads(line) for line in (case/'vision_observations.jsonl').open()];valid=[r for r in valid if 'point' in r and r.get('capture_ns',0)<=ns]
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
 req=GetPositionIK.Request();ik=req.ik_request;ik.group_name='manipulator_arm';ik.ik_link_name='reuse/tcp';ik.avoid_collisions=True;ik.robot_state=state(aq);ik.pose_stamped.header.frame_id='reuse/odom';ik.pose_stamped.pose=pose(pre,rot);ik.timeout.sec=1
 response=call('/compute_ik',req);report['padded_endpoint_ik_error_code']=response.error_code.val
 q=np.array(last['qpos']);command=q.copy()
 for i,value in enumerate(last['arm_target'],1):command[model.jnt_qposadr[model.joint('joint'+str(i)).id]]=value
 variants={'actual_base_actual_arm':q,'actual_base_commanded_arm':command}
 plans=json.loads((case/'pick_mission.json').read_text())['planning'];trajectory=next(r['trajectory']['joint_trajectory'] for r in plans if r.get('kind')=='plan' and r.get('error_code')==1)
 endpoint=np.array(anchor['qpos']);report['planned_goal_joints']=trajectory['joint_names']
 for name,value in zip(trajectory['joint_names'],trajectory['points'][-1]['positions']):endpoint[model.jnt_qposadr[model.joint(name).id]]=value
 variants['planned_endpoint']=endpoint;variants['anchor_start']=np.array(anchor['qpos'])
 motion_request=GetMotionPlan.Request();motion=motion_request.motion_plan_request
 motion.group_name='manipulator_arm';motion.pipeline_id='ompl';motion.planner_id='RRTConnectkConfigDefault';motion.num_planning_attempts=1;motion.allowed_planning_time=2.;motion.max_velocity_scaling_factor=.08;motion.max_acceleration_scaling_factor=.08;motion.start_state=state(np.array(anchor['qpos']))
 motion.workspace_parameters.header.frame_id='reuse/odom';motion.workspace_parameters.min_corner.x=-5.;motion.workspace_parameters.min_corner.y=-5.;motion.workspace_parameters.min_corner.z=-1.;motion.workspace_parameters.max_corner.x=5.;motion.workspace_parameters.max_corner.y=5.;motion.workspace_parameters.max_corner.z=3.
 constraint=Constraints()
 for name,value in zip(trajectory['joint_names'],trajectory['points'][-1]['positions']):constraint.joint_constraints.append(JointConstraint(joint_name=name,position=value,tolerance_above=.001,tolerance_below=.001,weight=1.))
 motion.goal_constraints=[constraint];planned=call('/plan_kinematic_path',motion_request,10.).motion_plan_response
 report['padded_joint_plan']=dict(error_code=planned.error_code.val,planning_time=planned.planning_time)
 if planned.error_code.val==1:
  path=planned.trajectory.joint_trajectory;report['padded_joint_plan'].update(trajectory=dict(names=list(path.joint_names),points=[dict(positions=list(p.positions),velocities=list(p.velocities),time_ns=p.time_from_start.sec*1_000_000_000+p.time_from_start.nanosec) for p in path.points]))
 for key,value in list(variants.items()):
  v=value.copy();v[:7]=anchor['qpos'][:7];variants['anchor_'+key]=v
 report.update(scope='post-exit actual v36 pre-grasp sample; installed MoveIt state validity versus native MuJoCo geometry; no engine/commands',case=case.name,last_sim_s=last['sim_s'],anchor_sim_s=anchor['sim_s'],actual_base=q[:7].tolist(),anchor_base=anchor['qpos'][:7],arm_command=list(last['arm_target']),actual_arm=[float(q[model.jnt_qposadr[model.joint('joint'+str(i)).id]]) for i in range(1,7)])
 for name,value in variants.items():
  req=GetStateValidity.Request();req.robot_state=state(value);req.group_name='manipulator_arm';v=call('/check_state_validity',req)
  d=mujoco.MjData(model);d.qpos[:]=value;mujoco.mj_forward(model,d)
  contacts=[dict(first=model.geom(int(c.geom[0])).name,second=model.geom(int(c.geom[1])).name,dist=float(c.dist)) for c in d.contact if any(model.body(int(model.geom_bodyid[g])).name=='link3' for g in map(int,c.geom))]
  distances=[]
  for a in range(model.ngeom):
   if model.body(int(model.geom_bodyid[a])).name!='link3' or not (model.geom_contype[a] or model.geom_conaffinity[a]):continue
   for b in range(model.ngeom):
    if model.geom_bodyid[b]!=0 or not (model.geom_contype[b] or model.geom_conaffinity[b]):continue
    segment=np.zeros(6);distance=mujoco.mj_geomDistance(model,d,a,b,.1,segment)
    distances.append(dict(robot_geom=model.geom(a).name,world_geom=model.geom(b).name,distance_m=float(distance),segment=segment.tolist()))
  report['rows'].append(dict(variant=name,moveit_valid=v.valid,moveit_contacts=[dict(first=c.contact_body_1,second=c.contact_body_2,depth=c.depth) for c in v.contacts],mujoco_contacts=contacts,closest_world=min(distances,key=lambda r:r['distance_m'])))
 response=call('/ch13/reuse/manipulation/planner/shutdown',Trigger.Request());report['shutdown_ack']=response.success;process.wait(timeout=8.);report['planner_exit']=process.returncode
finally:
 if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
 if node is not None:node.destroy_node();rclpy.try_shutdown()
 lock.close();(out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('case','last_sim_s','anchor_sim_s','rows','shutdown_ack','planner_exit')}))
