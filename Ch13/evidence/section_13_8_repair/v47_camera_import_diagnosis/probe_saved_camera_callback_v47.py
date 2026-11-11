"""Isolated sensor producer benchmark; no physics step, policy, action or lease."""
import os,sys,json,time,fcntl,types,subprocess,signal
from pathlib import Path
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);os.environ['ROS_DOMAIN_ID']='136';os.environ['CH13_PROBE_ROOT']=str(root)
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level2_obstacles'
for name in ('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_system_validation'):
 sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/name))
import numpy as np,mujoco,rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from ch13_navigation_reuse.platform_adapter import Platform
from ch13_navigation_reuse.state_adapter import adapt
from ch13_navigation_reuse.command_gateway import N,JOINT_NAMES
from ch13_navigation_reuse.sensors import SensorSuite
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.gc_timing import GCTiming
class PublisherProbe(Node):
 def __init__(self):
  super().__init__('capture_producer_component_probe');self.manipulation=object()
  for attr,kind,topic in [('clock_pub',Clock,'/clock'),('base_pub',Odometry,N+'/engine_state'),('nav_pub',Odometry,N+'/odometry'),('joint_pub',JointState,N+'/joint_states'),('tf_pub',TFMessage,'/tf')]:
   setattr(self,attr,self.create_publisher(kind,topic,1))
  self.static_pub=self.create_publisher(TFMessage,'/tf_static',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
  transform=TransformStamped();transform.header.frame_id='reuse/map';transform.child_frame_id='reuse/odom';transform.transform.rotation.w=1.
  self.static_pub.publish(TFMessage(transforms=[transform]))
 def publish_state(self,p,state):Platform.publish_state(self,p,state)
def stats(values):
 a=np.array(values);return dict(n=len(a),p50=float(np.quantile(a,.5)),p95=float(np.quantile(a,.95)),p99=float(np.quantile(a,.99)),maximum=float(a.max())) if len(a) else dict(n=0)
def main():
 out.mkdir(exist_ok=False);lock=(root.parent/'ch13_reuse_engine.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 original=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_13_8')
 case=original/'Ch13/evidence/section_13_8_system/09fda61e-5f05-4719-8f9b-9241409e74eb'
 saved=[json.loads(l) for l in (case/'engine_observations.jsonl').open()];saved=[r for r in saved if 82<=r['sim_s']<=86]
 model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml');data=mujoco.MjData(model)
 data.qpos[:]=saved[0]['qpos'];data.qvel[:]=saved[0]['qvel'];mujoco.mj_forward(model,data)
 rclpy.init(args=[]);node=PublisherProbe();suite=None;gc=GCTiming();gc.start();start=time.monotonic();error=None
 from ament_index_python.packages import get_package_prefix
 logs=[];children=[];child_exits=[]
 for name,command in [('ingress',[get_package_prefix('ch13_reuse_wire')+'/lib/ch13_reuse_wire/ingress','--manipulation']),('vision',[sys.executable,str(original.parent/'section_13_8_preparation_20261104/vision_callback_probe_v47.py'),'--report',str(out/'vision_summary.json'),'--inference-hz','10','--latest-camera','true','--target-shape','cylinder'])]:
  log=(out/(name+'.log')).open('w');logs.append(log);children.append((name,subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)))
 try:
  suite=SensorSuite(model,data,'vision',out,latest_camera=True);suite.attach(node)
  platform=types.SimpleNamespace(mjModel=model,mjData=data,_ch13_mujoco=mujoco,_ch13_sensors=suite)
  for row in saved[:300]:
   deadline=time.monotonic()+1/15.;data.qpos[:]=row['qpos'];data.qvel[:]=row['qvel'];mujoco.mj_forward(model,data)
   state=adapt(data.qpos[:27],data.qvel[:26],JOINT_NAMES,round(row['sim_s']*1e9));suite.step(platform,state)
   rclpy.spin_once(node,timeout_sec=0.);time.sleep(max(0.,deadline-time.monotonic()))
 finally:
  gc.stop()
  for name,child in reversed(children):
   child.send_signal(signal.SIGINT)
   try:child.wait(timeout=8.);forced=False
   except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=3.);forced=True
   child_exits.append(dict(name=name,returncode=child.returncode,forced=forced))
  for log in logs:log.close()
  if suite is not None:suite.close()
  node.destroy_node();rclpy.try_shutdown();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 producer=json.loads((out/'capture_stage_timing.json').read_text());render=json.loads((out/'renderer_captures.json').read_text())
 report=dict(scope='isolated domain136 sensor producer; reconstructed saved qpos only; no mj_step/policy/actuator/lease; does not reproduce full engine load',wall_s=time.monotonic()-start,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),producer={k:stats([x[k] for x in producer['rows']]) for k in ('scan_wall_s','state_publish_wall_s','pre_offer_wall_s','request_offer_wall_s')},renderer={k:stats([x['capture'][k] for x in render['captures']]) for k in ('request_to_render_wall_s','render_elapsed_cpu_s')},render_wall=stats([x['capture']['render_finished_wall']-x['capture']['render_started_wall'] for x in render['captures']]),gc=gc.summary(),camera_joined=suite.joined,camera_error=suite.camera.error)
 report['scope']='domain136 sensor producer with original C++ relay and actual vision; no physics/policy/planner/recorder/lease or actuator'
 report['child_exits']=child_exits
 if (out/'vision_summary.json').exists():
  vision=json.loads((out/'vision_summary.json').read_text());report['vision']={k:vision.get(k) for k in ('accepted','rejected','fault')}
 report['component_result']='PASS' if report['camera_joined'] and not report['camera_error'] and report.get('vision',{}).get('accepted',0)>50 and not report.get('vision',{}).get('fault') and not any(x['forced'] or x['returncode'] for x in child_exits) else 'FAIL'
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()