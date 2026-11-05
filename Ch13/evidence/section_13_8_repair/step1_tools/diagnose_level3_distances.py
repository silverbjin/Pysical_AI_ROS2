"""Post-exit saved-state MoveIt IK/collision probe. No engine or actuator goal."""
import fcntl,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='136'
import numpy as np,mujoco,rclpy,yaml
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import Transform
from moveit_msgs.msg import RobotState
from moveit_msgs.srv import GetPositionIK,GetStateValidity,ApplyPlanningScene
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
 clients={name:node.create_client(typ,name) for name,typ in [('/compute_ik',GetPositionIK),('/check_state_validity',GetStateValidity),('/apply_planning_scene',ApplyPlanningScene),('/ch13/reuse/manipulation/planner/shutdown',Trigger)]}
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
 for uuid in ids[:1]:
  case=root/'Ch13/evidence/section_13_8_system'/uuid
  stages=json.loads((case/'pick_mission.json').read_text())['stages'];ns=next(r['clock_ns'] for r in stages if r.get('phase')=='PRE_GRASP')
  samples=[json.loads(line) for line in (case/'engine_observations.jsonl').open()];sample=min(samples,key=lambda r:abs(r['sim_s']-ns/1e9));q=np.array(sample['qpos'])
  observations=[json.loads(line) for line in (case/'vision_observations.jsonl').open()]
  # The log may wrap accepted observations; preserve its actual schema explicitly.
  valid=[r for r in observations if 'point' in r and r.get('capture_ns',0)<=ns];assert valid,'no saved admitted point'
  observation=max(valid,key=lambda r:r['capture_ns']);center=np.array(observation['point'])
  apply=ApplyPlanningScene.Request();apply.scene.is_diff=True;apply.scene.robot_state.is_diff=True
  apply.scene.world.collision_objects=[object_box('ground',[0,0,-.01],[20,20,.02])]+[object_box('reuse_'+n,c,2*np.array(z)) for n,c,z in layout('vision') if n!='target']+planning_objects(scenario)+[object_cylinder('pick_target',center)]
  assert call('/apply_planning_scene',apply).success
  forward=center-np.array([*q[:2],center[2]]);forward/=np.linalg.norm(forward)
  for distance in (.60,.65,.70):
   q[:2]=center[:2]-distance*forward[:2]
   for sign in (1.,-1.):
    pre,rot=grasp_pose(center,forward,sign,scenario)
    for stage,point in [('pre_grasp',pre),('grasp',center)]:
     row=dict(distance=distance,uuid=uuid,stage=stage,sign=sign,source_stamp_ns=observation['capture_ns'],sample_sim_s=sample['sim_s'],base_qpos=q[:7].tolist(),point=point.tolist(),solutions={})
     for avoid in (False,True):
      req=GetPositionIK.Request();ik=req.ik_request;ik.group_name='manipulator_arm';ik.ik_link_name='reuse/tcp';ik.avoid_collisions=avoid;ik.robot_state=state(q);ik.pose_stamped.header.frame_id='reuse/odom';ik.pose_stamped.pose=pose(point,rot);ik.timeout.sec=1
      response=call('/compute_ik',req);result=dict(error_code=response.error_code.val)
      if response.error_code.val==1:
       validity=GetStateValidity.Request();validity.robot_state=response.solution;validity.group_name='manipulator_arm';v=call('/check_state_validity',validity)
       values=dict(zip(response.solution.joint_state.name,response.solution.joint_state.position));fk=urdf_fk(config['robot_description'],values)['reuse/tcp'];world=np.eye(4);world[:3,:3]=Rotation.from_quat(np.roll(q[3:7],-1)).as_matrix();world[:3,3]=q[:3];fk=world@fk
       result.update(q_arm=[values[j] for j in JOINTS],state_valid=v.valid,contacts=[dict(first=c.contact_body_1,second=c.contact_body_2,depth=c.depth) for c in v.contacts],position_residual_m=float(np.linalg.norm(fk[:3,3]-point)),rotation_residual_rad=float((Rotation.from_matrix(fk[:3,:3]).inv()*rot).magnitude()))
      row['solutions'][str(avoid)]=result
     report['rows'].append(row)
  print('SAVED_CASE_DONE',uuid,flush=True)
 # Reconstruct last actual qpos/contact geometry of the v29 navigation failure.
 case=root/'Ch13/evidence/section_13_8_system/b2feddf0-745f-4728-92dd-5aed5fab4d3b'
 for line in (case/'engine_observations.jsonl').open():last=json.loads(line)
 d=mujoco.MjData(model);d.qpos[:]=last['qpos'];d.qvel[:]=last['qvel'];mujoco.mj_forward(model,d)
 for contact in d.contact:
  a,b=map(int,contact.geom);an=model.body(model.geom_bodyid[a]).name;bn=model.body(model.geom_bodyid[b]).name
  if (model.geom_group[a]==5 or model.geom_group[b]==5) and ('foot' in an or 'foot' in bn):
   report['contacts_v29'].append(dict(first=an,second=bn,geom_first=model.geom(a).name,geom_second=model.geom(b).name,position=contact.pos.tolist(),distance=float(contact.dist)))
 near=[]
 for a in range(model.ngeom):
  if 'foot' not in model.body(model.geom_bodyid[a]).name:continue
  for b in range(model.ngeom):
   if model.geom_group[b]!=5:continue
   segment=np.zeros(6);distance=mujoco.mj_geomDistance(model,d,a,b,1.,segment)
   near.append(dict(foot=model.body(model.geom_bodyid[a]).name,geom=model.geom(b).name,distance=float(distance),segment=segment.tolist()))
 report['nearest_v29_foot_world']=sorted(near,key=lambda r:r['distance'])[:8]
 report['last_v29_base']=last['qpos'][:7];report['last_v29_sim_s']=last['sim_s']
 response=call('/ch13/reuse/manipulation/planner/shutdown',Trigger.Request());report['shutdown_ack']=response.success;process.wait(timeout=8.);report['planner_exit']=process.returncode
finally:
 if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
 if node is not None:node.destroy_node();rclpy.try_shutdown()
 lock.close();(out/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print('DIAGNOSTIC_ROWS',len(report['rows']),'CONTACTS',report['contacts_v29'])
