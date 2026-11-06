"""Vision-sourced approach admission and final position-only arm workspace audit."""
import json,math,time,os
from pathlib import Path
import numpy as np
import mujoco
from rclpy.action import ActionClient
from nav2_msgs.action import ComputePathToPose
from ch13_navigation_reuse.approach_geometry import candidates,position_ik,footprint_clear
from ch13_navigation_reuse.vision_geometry import admissible
from ch13_navigation_reuse.command_gateway import set_stamp

def wait_new_capture(until,get_observation,get_clock,timeout=3):
 previous=get_observation()['capture_ns'] if get_observation() is not None else 0
 def fresh_new():
  value=get_observation()
  return value is not None and value['capture_ns']>previous and admissible(value['capture_ns'],value['capture_wall'],get_clock(),time.monotonic(),value['tf_stamp_ns'])
 assert until(fresh_new,timeout),'no new original capture after planning'
 return get_observation()

def current_q(state,joints):
 q=np.zeros(27);p=state.pose.pose.position;r=state.pose.pose.orientation;q[:7]=[p.x,p.y,p.z,r.w,r.x,r.y,r.z];q[7:]=list(joints.position);return q

def select_goal(root,node,until,get_observation,get_state,get_joints,get_grid,get_clock,*,record_paths=None):
 from ch13_navigation_reuse.scene import make_model
 model=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision');fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint'];planner=ActionClient(node,ComputePathToPose,'/compute_path_to_pose')
 def fresh(observation):return observation is not None and admissible(observation['capture_ns'],observation['capture_wall'],get_clock(),time.monotonic(),observation['tf_stamp_ns'])
 assert until(lambda:fresh(get_observation()) and get_joints() is not None and get_grid() is not None and planner.server_is_ready(),8),'no fresh actual RGB-D observation/TF/map'
 initial=get_observation();point=np.array(initial['point']);q=current_q(get_state(),get_joints());grid=get_grid()
 distances=None;bearing_options={};audit_paths=False
 if os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1':
  from ch13_system_validation.scenarios import active_scenario
  standoff=active_scenario().approach_standoff_m
  if standoff is not None:distances=(standoff,)
  bearings=active_scenario().approach_bearings
  if bearings is not None:bearing_options['bearings']=bearings
  audit_paths=(active_scenario().world in ('obstacles','house') and os.environ.get('CH13_EXPERIMENTAL_SE2')=='1')
 choices=candidates(model,q,point,grid,fp,distances=distances,**bearing_options);assert choices,'no collision-free arm-reachable approach candidate'
 evaluated=[];path_checks=[]
 def path_cost(pose,stamp):
  goal=ComputePathToPose.Goal();goal.goal.header.frame_id='reuse/map';set_stamp(goal.goal.header.stamp,stamp);goal.goal.pose.position.x=pose[0];goal.goal.pose.position.y=pose[1];goal.goal.pose.orientation.z=math.sin(pose[2]/2);goal.goal.pose.orientation.w=math.cos(pose[2]/2);goal.planner_id='GridBased';goal.use_start=False
  sent=planner.send_goal_async(goal);assert until(sent.done,3),'candidate planner admission deadline';handle=sent.result()
  if not handle.accepted:return None
  result=handle.get_result_async();assert until(result.done,3),'candidate planner terminal deadline';value=result.result()
  if value.status!=4 or not value.result.path.poses:
   if audit_paths:
    path_checks.append(dict(target=list(pose),valid=False,nav2_status=value.status,nav2_error_code=getattr(value.result,'error_code',None)))
    if record_paths is not None:record_paths(path_checks)
   return None
  if audit_paths:
   from concurrent.futures import ThreadPoolExecutor
   from ch13_navigation_reuse.path_geometry import path_footprint_clear
   poses=[[p.pose.position.x,p.pose.position.y,2*math.atan2(p.pose.orientation.z,p.pose.orientation.w)] for p in value.result.path.poses]
   if value.result.path.header.frame_id!='reuse/map':return None
   with ThreadPoolExecutor(max_workers=1,thread_name_prefix='reuse_route_geometry') as compute:
    checked=compute.submit(path_footprint_clear,poses,grid,fp)
    assert until(checked.done,5.),'filled footprint path audit deadline'
    valid=checked.result()
   path_checks.append(dict(target=list(pose),valid=valid,poses=poses,scope='filled pinned footprint and original static occupancy; no physical success claim'))
   if record_paths is not None:record_paths(path_checks)
   if not valid:return None
  points=[(p.pose.position.x,p.pose.position.y) for p in value.result.path.poses];return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
 for candidate in choices[:3]:
  cost=path_cost(candidate['pose'],initial['capture_ns'])
  if cost is not None:evaluated.append(dict(candidate,path_cost_m=cost))
 assert evaluated,'all reachable candidates blocked by Nav2 planner'
 selected=min(evaluated,key=lambda c:c['path_cost_m'])
 for attempt in range(2):
  latest=wait_new_capture(until,get_observation,get_clock);observed=np.array(latest['point']);delta=observed-point;assert np.linalg.norm(delta)<.03,'object moved beyond static-fixture assumption'
  pose=list(selected['pose']);pose[0]+=float(delta[0]);pose[1]+=float(delta[1]);trial=current_q(get_state(),get_joints());trial[:2]=pose[:2];trial[3:7]=[math.cos(pose[2]/2),0,0,math.sin(pose[2]/2)];ik=position_ik(model,trial,observed)
  if ik is not None and footprint_clear(pose,grid,fp) and fresh(latest):
   if audit_paths:
    final_cost=path_cost(pose,latest['capture_ns'])
    if final_cost is None or not fresh(latest):continue
    selected=dict(selected,path_cost_m=final_cost)
   return pose,{'ranking_capture_ns':initial['capture_ns'],'source_observation':latest,'candidate_evaluations':evaluated,'candidate_path_checks':path_checks,'selected':dict(selected,pose=pose,final_ik=ik),'arm_model_source':'pinned mount/joints, position-only FK/Jacobian IK; no arm commands'},model
 raise AssertionError('fresh candidate admission could not be completed')
