"""Synthetic DDS cost fixture. NO engine, commands, admission or physics proof."""
import cProfile,hashlib,json,os,pstats,select,shutil,signal,subprocess,sys,threading,time,uuid
from pathlib import Path
os.environ['ROS_DOMAIN_ID']='228'
repo=Path.cwd();sys.path.insert(0,str(repo/'Ch13/scripts'))
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Point,TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState,Imu,LaserScan
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from integrated_robot_interfaces.msg import FootContacts,MotionState
from geometry_msgs.msg import PoseStamped
from tf2_msgs.msg import TFMessage

if len(sys.argv)>1 and sys.argv[1]=='publisher':
    rclpy.init();node=Node('synthetic_probe_cost_source');stop=threading.Event()
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    def pub(kind,topic,qos=qos_profile_sensor_data):return node.create_publisher(kind,topic,qos)
    clock=pub(Clock,'/clock');joints=pub(JointState,'/joint_states')
    body=pub(Odometry,'/odom');feet=pub(FootContacts,'/navigation/foot_contacts')
    imu=pub(Imu,'/navigation/imu');scan=pub(LaserScan,'/scan');com=pub(PoseStamped,'/navigation/native_com')
    controls=pub(String,'/navigation/native_controls',100);tf=pub(TFMessage,'/tf')
    motions={k:pub(MotionState,'/navigation/'+k+'_state',10) for k in ('crawl','carry','guard','startup')}
    q=JointState(name=['fixture_joint_'+str(i) for i in range(20)],position=[0.]*20,velocity=[0.]*20)
    b=Odometry();b.header.frame_id='odom';b.child_frame_id='base_footprint';b.pose.pose.orientation.w=1.;b.pose.pose.position.z=.46
    f=FootContacts(names=['fr_foot','fl_foot','rr_foot','rl_foot'],points=[Point(z=0.) for _ in range(4)],
                   normal_forces=[30.]*4,touching=[True]*4)
    f.header.frame_id='odom'
    im=Imu();im.header.frame_id='base_link';im.linear_acceleration.z=9.81
    s=LaserScan(angle_min=-3.14,angle_increment=6.28/360,range_min=.05,range_max=10.,ranges=[2.]*360)
    s.header.frame_id='lidar_link'
    p=PoseStamped();p.header.frame_id='odom';p.pose.position.z=.4;p.pose.orientation.w=1.
    mts=MotionState(state='STAND',ready=True,stopped=True,model_sha256='synthetic-cost-fixture')
    transforms=[]
    for i in range(20):
        tr=TransformStamped();tr.header.frame_id='fixture_root';tr.child_frame_id='fixture_link_'+str(i);tr.transform.rotation.w=1.;transforms.append(tr)
    packet=dict(schema=1,epoch=0,capture_ns=0,sequence=0,synthetic_fixture=True,actuators=[dict(
        actuator_id=i,ctrl_index=i,output_index=i,joint_name='fixture_joint_'+str(i),joint_type='hinge',
        control_kind='position',position=0.,velocity=0.,ctrl=0.,actuator_force=0.,joint_force=0.,kp=100.,kv=10.,
        gear=1.,force_limited=True,ctrl_limited=True,force_range=[-30.,30.],ctrl_range=[-2.,2.]) for i in range(20)])
    start=time.monotonic();next_tick=start;index=0
    print('READY',flush=True)
    try:
        while not stop.is_set():
            now=time.monotonic()-start+1.;msg=Clock();msg.clock.sec=int(now);msg.clock.nanosec=int((now-int(now))*1e9)
            stamp=msg.clock;clock.publish(msg);index+=1
            if index%5==0:q.header.stamp=stamp;joints.publish(q)
            if index%10==0:
                for value in (b,f,im,p,mts,s):value.header.stamp=stamp
                body.publish(b);f.sequence=index;feet.publish(f);imu.publish(im);com.publish(p)
                for publisher in motions.values():publisher.publish(mts)
                packet.update(capture_ns=stamp.sec*1_000_000_000+stamp.nanosec,sequence=index)
                controls.publish(String(data=json.dumps(packet)))
            if index%5==0:
                for tr in transforms:tr.header.stamp=stamp
                tf.publish(TFMessage(transforms=transforms))
            if index%50==0:scan.publish(s)
            next_tick+=.002;stop.wait(max(0.,next_tick-time.monotonic()))
    finally:node.destroy_node();rclpy.try_shutdown()
    raise SystemExit(0)

from probe_navigation_13_5 import NavigationProbe,ProbeReceiver
key=str(uuid.uuid4());native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')/('probe-cost-'+key)
native.mkdir();reports=[];profiles={};original=ProbeReceiver._spin;target=None
def profiled(self):
    if self.node.get_name()!=target:return original(self)
    profile=cProfile.Profile()
    profile.enable()
    try:original(self)
    finally:
        profile.disable();stats=pstats.Stats(profile)
        rows=[dict(file=k[0],line=k[1],function=k[2],calls=v[1],self_cpu_s=v[2],cumulative_cpu_s=v[3]) for k,v in stats.stats.items()]
        profiles[self.node.get_name()]=sorted(rows,key=lambda r:-r['self_cpu_s'])[:30]
        profile.dump_stats(str(native/(self.node.get_name()+'.pstats')))
peer=subprocess.Popen([sys.executable,__file__,'publisher'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
try:
    if not select.select([peer.stdout],[],[],10.)[0] or peer.stdout.readline().strip()!='READY':raise RuntimeError('synthetic peer not ready')
    rclpy.init()
    ProbeReceiver._spin=profiled
    for target in (None,'navigation_native_probe','navigation_probe_recording'):
        directory=native/(target or 'baseline');directory.mkdir()
        probe=NavigationProbe(directory,engine='gazebo',bounded_history=True);receiver=ProbeReceiver(probe)
        report=dict(profile_target=target)
        try:
            time.sleep(1.);start=time.monotonic();cpu=time.process_time();time.sleep(4.)
            duration=time.monotonic()-start;used=time.process_time()-cpu
            receiver.check()
            report.update(wall_s=duration,process_cpu_s=used,one_core_percent=100*used/duration,
                        contacts=probe.callback_costs.get('_sensor:contacts'),timing=probe.timing_snapshot())
        finally:
            assert receiver.shutdown(timeout_sec=5.)
            report['receivers']=receiver.report();probe.close_log();probe.destroy_node()
        reports.append(report)
    rclpy.try_shutdown()
finally:
    ProbeReceiver._spin=original
    peer.send_signal(signal.SIGINT);stdout,stderr=peer.communicate(timeout=10.)
    assert peer.returncode==0,(stdout,stderr)
out=dict(scope='synthetic_DDS_CPU_fixture_not_engine_or_safety_acceptance',domain=228,
    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reports=reports,
    thread_cpu_profiles=profiles,source_peer_reaped=True,source_peer_exit=peer.returncode)
with (native/'result.json').open('x') as file:json.dump(out,file,indent=2)
destination=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'/native.name
shutil.copytree(native,destination)
for source in native.rglob('*'):
    if source.is_file():assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256((destination/source.relative_to(native)).read_bytes()).digest()
print(json.dumps(dict(output=str(destination),reports=[{k:v for k,v in r.items() if k not in ('timing','contacts','receivers')} for r in reports],
    profiles={k:v[:10] for k,v in profiles.items()},peer_reaped=True),indent=2))
