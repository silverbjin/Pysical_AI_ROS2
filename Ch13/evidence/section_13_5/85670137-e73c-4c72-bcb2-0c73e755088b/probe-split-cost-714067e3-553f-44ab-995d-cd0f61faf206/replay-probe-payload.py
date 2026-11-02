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
    if len(sys.argv)>2:
        fixture=json.loads(Path(sys.argv[2]).read_text());samples=fixture['frame']['samples']
        d=samples['joints']['data'];q.name=list(d['position']);q.position=list(d['position'].values());q.velocity=[d['velocity'][n] for n in q.name]
        d=samples['body']['data'];b.pose.pose.position.x,b.pose.pose.position.y,b.pose.pose.position.z=d['position']
        b.pose.pose.orientation.x,b.pose.pose.orientation.y,b.pose.pose.orientation.z,b.pose.pose.orientation.w=d['orientation']
        b.twist.twist.linear.x,b.twist.twist.linear.y,b.twist.twist.linear.z=d['linear_velocity']
        b.twist.twist.angular.x,b.twist.twist.angular.y,b.twist.twist.angular.z=d['angular_velocity']
        d=samples['contacts']['data'];f.names=d['names'];f.points=[Point(x=a,y=c,z=e) for a,c,e in d['points']];f.normal_forces=d['forces'];f.touching=d['touching'];f.unexpected_contacts=d['unexpected_contacts']
        d=samples['imu']['data'];im.linear_acceleration.x,im.linear_acceleration.y,im.linear_acceleration.z=d['acceleration'];im.angular_velocity.x,im.angular_velocity.y,im.angular_velocity.z=d['angular_velocity']
        d=samples['scan']['data'];s.angle_min=d['angle_min'];s.angle_increment=d['angle_increment'];s.range_min=d['range_min'];s.range_max=d['range_max'];s.ranges=[r if hit else float('inf') for r,hit in zip(d['ranges'],d['hits'])]
        p.pose.position.x,p.pose.position.y,p.pose.position.z=samples['native_com']['data']
        mts.model_sha256=samples['carry']['data']['model_sha256'];packet=fixture['native_controls']
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

