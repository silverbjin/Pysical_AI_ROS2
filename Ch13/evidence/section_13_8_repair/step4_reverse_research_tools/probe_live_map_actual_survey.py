"""Installed NavFn/Smac Hybrid planning-only comparison on the same saved world."""
import fcntl,json,math,os,signal,subprocess,sys,time
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='137';os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level3_house'
import rclpy,yaml
import xml.etree.ElementTree as ET
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import ComputePathToPose
from lifecycle_msgs.srv import ChangeState
from nav2_msgs.srv import GetCostmap
from rcl_interfaces.srv import GetParameters
from rosidl_runtime_py.convert import message_to_ordereddict
from tf2_ros import StaticTransformBroadcaster
from ch13_navigation_reuse.scene import map_layout
from ch13_navigation_reuse.approach_geometry import footprint_clear
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=False,parents=True)
params=yaml.safe_load((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/nav2_params.yaml').read_text())
def no_sim(d):
 if isinstance(d,dict):
  for k,v in d.items():
   if k=='use_sim_time':d[k]=False
   else:no_sim(v)
no_sim(params)
server=params['planner_server']['ros__parameters'];server['planner_plugins']=['HeadingAware']
server['HeadingAware']=dict(plugin=ET.parse('/opt/ros/jazzy/share/nav2_smac_planner/smac_plugin_hybrid.xml').getroot().find('class').attrib['type'],motion_model_for_search='DUBIN',minimum_turning_radius=.3,angle_quantization_bins=72,tolerance=.01,allow_unknown=False,max_planning_time=2.,smooth_path=False,downsample_costmap=False,cache_obstacle_heuristic=False)
global_params=params['global_costmap']['global_costmap']['ros__parameters'];global_params['plugins']=['static_layer','inflation_layer']
(out/'planner.yaml').write_text(yaml.safe_dump(params))
report=dict(scope='planning only: same known static occupancy and footprint, no engine/action commands; dynamic scan/attached-object physics not represented',rows=[],result='ERROR')
lock=(root.parent/'ch13_reuse_engine.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
node=None;process=None
try:
 rclpy.init();node=rclpy.create_node('heading_planner_comparison')
 qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
 pub=node.create_publisher(OccupancyGrid,'/ch13/reuse/map',qos);grid=OccupancyGrid();grid.header.frame_id='reuse/map';grid.info.resolution=.05;grid.info.width=120;grid.info.height=100;grid.info.origin.position.x=-2.;grid.info.origin.position.y=-2.5;grid.info.origin.orientation.w=1.
 obstacles=map_layout('vision')
 grid.data=[100 if any(abs(-2+(x+.5)*.05-p[0])<=z[0]+.025 and abs(-2.5+(y+.5)*.05-p[1])<=z[1]+.025 for _,p,z in obstacles) else 0 for y in range(100) for x in range(120)]
 broadcaster=StaticTransformBroadcaster(node);transforms=[]
 for parent,child in [('reuse/map','reuse/odom'),('reuse/odom','reuse/nav_base')]:
  t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child;t.transform.rotation.w=1.;transforms.append(t)
 broadcaster.sendTransform(transforms);pub.publish(grid)
 life=node.create_client(ChangeState,'/planner_server/change_state');client=ActionClient(node,ComputePathToPose,'/compute_path_to_pose')
 assert not life.service_is_ready(),'another planner in diagnostic domain'
 process=subprocess.Popen(['/opt/ros/jazzy/lib/nav2_planner/planner_server','--ros-args','--params-file',str(out/'planner.yaml')],stdout=(out/'planner.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 def until(predicate,seconds):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   rclpy.spin_once(node,timeout_sec=.01)
   if predicate():return True
   if process.poll() is not None:raise RuntimeError('owned planner exited')
  return False
 assert until(life.service_is_ready,20.)
 def transition(value):
  req=ChangeState.Request();req.transition.id=value;f=life.call_async(req);assert until(f.done,15.);assert f.result().success
 transition(1);transition(3);assert until(client.server_is_ready,10.)
 # Static publication and transform ownership remain solely with this node.
 pub.publish(grid);assert until(lambda:False,1.) is False
 map_client=node.create_client(GetCostmap,'/global_costmap/get_costmap')
 assert until(map_client.service_is_ready,3.)
 mf=map_client.call_async(GetCostmap.Request());assert until(mf.done,3.);cm=mf.result().map
 report['costmap']=message_to_ordereddict(cm)
 gp=node.create_client(GetParameters,'/global_costmap/global_costmap/get_parameters')
 assert until(gp.service_is_ready,3.);req=GetParameters.Request();req.names=['footprint','robot_radius','footprint_padding']
 pf=gp.call_async(req);assert until(pf.done,3.);report['costmap_parameters']=message_to_ordereddict(pf.result())
 fp=json.loads(pf.result().values[0].string_value);fp=[[x+math.copysign(.01,x),y+math.copysign(.01,y)] for x,y in fp]
 lethal=dict(width=cm.metadata.size_x,height=cm.metadata.size_y,resolution=cm.metadata.resolution,origin=[cm.metadata.origin.position.x,cm.metadata.origin.position.y],data=[100 if v>=254 else 0 for v in cm.data])
 def make_pose(target):
  from geometry_msgs.msg import PoseStamped
  p=PoseStamped();p.header.frame_id='reuse/map';p.pose.position.x,p.pose.position.y=map(float,target[:2]);p.pose.orientation.z=math.sin(target[2]/2);p.pose.orientation.w=math.cos(target[2]/2);return p
 actual=root/'Ch13/evidence/section_13_8_system/9e160887-cc8a-4f1d-a4e7-83aae4f77818'
 observations=[json.loads(line) for line in (actual/'engine_observations.jsonl').open()]
 row=min(observations,key=lambda r:abs(r['sim_s']-18.96));q=row['qpos'];w,x,y,z=q[3:7];yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
 actual_start=(q[0],q[1],yaw);summary=json.loads((actual/'navigation_summary.json').read_text());actual_target=summary['vision_path_checks'][0]['target']
 cases=[('actual_start_exact_target',actual_start,actual_target),('ideal_start_exact_target',(1.9,.4,math.atan2(.6,1.1)),actual_target),('actual_start_ideal_target',actual_start,(3.,1.6,-math.pi/2)),('ideal_start_ideal_target',(1.9,.4,math.atan2(.6,1.1)),(3.,1.6,-math.pi/2))]
 for label,start,target in cases:
  for planner in ('HeadingAware',):
   goal=ComputePathToPose.Goal();goal.start=make_pose(start);goal.goal=make_pose(target);goal.use_start=True;goal.planner_id=planner
   start_wall=time.monotonic();sent=client.send_goal_async(goal);assert until(sent.done,3.);handle=sent.result();assert handle.accepted
   f=handle.get_result_async();assert until(f.done,6.);result=f.result();path=result.result.path.poses
   points=[[p.pose.position.x,p.pose.position.y,2*math.atan2(p.pose.orientation.z,p.pose.orientation.w)] for p in path]
   invalid=sum(not footprint_clear(p,lethal,fp) for p in points)
   row=dict(invalid_filled_footprints=invalid,case=label,planner=planner,start=start,target=target,status=result.status,error_code=getattr(result.result,'error_code',None),wall_s=time.monotonic()-start_wall,poses=points)
   if len(points)>1:
    last=points[-1];previous=next(p for p in reversed(points[:-1]) if math.dist(p[:2],last[:2])>.04)
    tangent=math.atan2(last[1]-previous[1],last[0]-previous[0]);row.update(length_m=sum(math.dist(a[:2],b[:2]) for a,b in zip(points,points[1:])),last_position_error_m=math.dist(last[:2],target[:2]),final_tangent_yaw=tangent,final_tangent_error_rad=abs(math.atan2(math.sin(tangent-target[2]),math.cos(tangent-target[2]))))
   report['rows'].append(row);print(label,planner,{k:v for k,v in row.items() if k!='poses'},flush=True)
 # A new full map from the same original publisher, not a new planner or TF.
 before_cost=int(cm.data[int((1.+2.5)/cm.metadata.resolution)*cm.metadata.size_x+int((3.+2.)/cm.metadata.resolution)])
 obstacles=[g for g in obstacles if g[0]!='target']
 grid.data=[100 if any(abs(-2+(x+.5)*.05-p[0])<=z[0]+.025 and abs(-2.5+(y+.5)*.05-p[1])<=z[1]+.025 for _,p,z in obstacles) else 0 for y in range(100) for x in range(120)]
 grid.header.stamp=node.get_clock().now().to_msg();pub.publish(grid)
 pending=None;changed=None
 def map_updated():
  global pending,changed
  if pending is None:pending=map_client.call_async(GetCostmap.Request())
  if not pending.done():return False
  changed=pending.result().map;pending=None;m=changed.metadata
  x=int((3.+2.)/m.resolution);y=int((1.+2.5)/m.resolution)
  return changed.data[y*m.size_x+x]<253
 assert until(map_updated,3.),'full map update did not clear original target'
 m=changed.metadata;x=int((3.+2.)/m.resolution);y=int((1.+2.5)/m.resolution)
 report['map_update']=dict(before_target_cost=before_cost,after_target_cost=int(changed.data[y*m.size_x+x]),update_time=message_to_ordereddict(m.update_time))
 lethal['data']=[100 if v>=254 else 0 for v in changed.data]
 goal=ComputePathToPose.Goal();goal.start=make_pose((3.,1.6,-math.pi/2));goal.goal=make_pose((0.,0.,math.pi));goal.use_start=True;goal.planner_id='HeadingAware'
 sent=client.send_goal_async(goal);assert until(sent.done,3.);handle=sent.result();assert handle.accepted
 future=handle.get_result_async();assert until(future.done,6.);result=future.result()
 points=[[p.pose.position.x,p.pose.position.y,2*math.atan2(p.pose.orientation.z,p.pose.orientation.w)] for p in result.result.path.poses]
 report['post_update_return']=dict(status=result.status,error_code=result.result.error_code,poses=points,invalid_filled_footprints=sum(not footprint_clear(p,lethal,fp) for p in points))
 print('MAP_UPDATE',report['map_update'],'RETURN',{k:v for k,v in report['post_update_return'].items() if k!='poses'},flush=True)
 transition(4);transition(2);process.send_signal(signal.SIGINT);process.wait(timeout=8.);report['planner_exit']=process.returncode;report['result']='COMPLETED'
finally:
 if process is not None and process.poll() is None:process.send_signal(signal.SIGINT);process.wait(timeout=8.)
 if node is not None:node.destroy_node();rclpy.try_shutdown()
 lock.close();(out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
