"""Controlled DDS stream cost in an inactive owner, not an engine trial."""
import json,sys,time,threading,hashlib
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point,Vector3
from rosgraph_msgs.msg import Clock
from integrated_robot_interfaces.msg import FootContacts
root=Path.cwd();sys.path.insert(0,str(root/'Ch13/ros2_ws/src/integrated_robot_navigation'))
from integrated_robot_navigation.crawl_controller import CrawlController
from integrated_robot_navigation.clock_execution import make_control_executor
from integrated_robot_navigation.ingress_dispatch import IngressDispatch
mode=sys.argv[1];assert mode in ('waitset','events')
start_original=IngressDispatch.start
def before_start(self):
    self.select_backend(mode);return start_original(self)
IngressDispatch.start=before_start
ctx=Context();rclpy.init(context=ctx)
node=CrawlController(engine='gazebo',context=ctx,cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],
    parameter_overrides=[Parameter('use_sim_time',value=True),Parameter('validation_mode',value=True),
        Parameter('control_clock_mode',value='relay100')])
peer=Node('ingress_cost_peer',context=ctx);executor=make_control_executor(node);executor.add_node(node)
base=root/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
path=base/'native-g1-gazebo-330b055b-0cb9-4db5-872d-06e2613fe447/controller_report.json'
report=json.loads(path.read_text());samples=report['first_fault']['samples']
q=samples['joints']['data'];names=list(q['position']);joint=JointState(name=names,
    position=[q['position'][n] for n in names],velocity=[q['velocity'][n] for n in names])
imu=Imu();imu.header.frame_id=samples['imu']['frame_id'];imu.linear_acceleration.z=9.81
body=Odometry();body.header.frame_id='odom';body.child_frame_id='base_footprint';body.pose.pose.orientation.w=1.
c=samples['contacts']['data'];contact=FootContacts(names=c['names'],normal_forces=c['forces'],
    touching=c['touching'],points=[Point(x=p[0],y=p[1],z=p[2]) for p in c['points']],
    forces_world=[Vector3(x=f[0],y=f[1],z=f[2]) for f in c['forces_world']],force_vectors_valid=True)
contact.header.frame_id='odom'
# Use the actual configured subscription topics, never guess hardware names.
types={JointState:joint,Imu:imu,Odometry:body,FootContacts:contact,Clock:Clock()}
pubs=[]
for sub in node.ingress_worker.node.subscriptions:
    kind=sub.msg_type
    if kind in types:pubs.append((peer.create_publisher(kind,sub.topic_name,qos_profile_sensor_data),types[kind]))
assert len(pubs)==5
counts={type(msg).__name__:0 for _,msg in pubs};stop=threading.Event();failures=[]
def publish():
    try:
        index=0;due=time.monotonic()
        while not stop.is_set():
            ns=17_000_000_000+index*10_000_000
            for pub,msg in pubs:
                if isinstance(msg,Clock):stamp=msg.clock
                elif index%2:continue
                else:stamp=msg.header.stamp
                stamp.sec,stamp.nanosec=divmod(ns,1_000_000_000);pub.publish(msg);counts[type(msg).__name__]+=1
            index+=1;due+=.01;stop.wait(max(0.,due-time.monotonic()))
    except BaseException as error:failures.append(repr(error))
thread=threading.Thread(target=publish,daemon=False);thread.start();begin=time.monotonic_ns();cpu=time.process_time_ns()
try:
    while time.monotonic_ns()-begin<3_000_000_000:executor.spin_once(timeout_sec=.01)
    wall=time.monotonic_ns()-begin;used=time.process_time_ns()-cpu
    assert not node.active and node.command_publication_count==0 and node.contact_ingress
finally:
    stop.set();thread.join(2.);assert not thread.is_alive()
    executor.shutdown(timeout_sec=2.);node.destroy_node();peer.destroy_node();ctx.try_shutdown()
assert not failures
out=dict(scope='controlled_DDS_inactive_owner_no_engine_or_motor',mode=mode,
    cpu_ns=used,wall_ns=wall,cpu_percent=used/wall*100.,published=counts,
    ingress=node.ingress_worker.snapshot(),no_motor_publications=True,
    report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
output=base/('task8-g1-ingress-'+mode+'-01.json');assert not output.exists();output.write_text(json.dumps(out,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(out))
