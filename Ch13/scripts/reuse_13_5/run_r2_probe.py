"""Bounded actual R2 acceptance probe; starts only this task's owned processes."""
import argparse,json,os,subprocess,sys,time,traceback,math,re,signal
from pathlib import Path
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rcl_interfaces.srv import SetParametersAtomically
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType
from ch13_navigation_reuse.command_gateway import N,ns,set_stamp

def service_call(node,name,request,until,clients,service=Trigger,timeout=3):
    client=clients.get(name)
    if client is None:client=clients.setdefault(name,node.create_client(service,name))
    assert until(client.service_is_ready,timeout),'missing service '+name
    future=client.call_async(request);assert until(future.done,timeout),'service deadline '+name
    return future.result()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo-root',required=True);parser.add_argument('--evidence',required=True);parser.add_argument('--startup-timeout',type=float,default=20.);parser.add_argument('--launch',action='store_true');a=parser.parse_args()
    root=Path(a.repo_root);out=Path(a.evidence);out.mkdir(parents=True,exist_ok=True)
    children=[];logs=[];S={'result':'FAIL','pid':os.getpid(),'events':[]};node=None
    try:
        commands=[('ingress',['/home/jinho/ch13_reuse_r2_build/install/ch13_reuse_wire/lib/ch13_reuse_wire/ingress']),('gateway',[sys.executable,'-m','ch13_navigation_reuse.command_gateway']),('platform',[sys.executable,'-m','ch13_navigation_reuse.platform_adapter','--repo-root',str(root),'--max-sim-s','40','--report',str(out/'engine.json')])]
        if a.launch:commands=[('launch',['/usr/bin/python3','/opt/ros/jazzy/bin/ros2','launch','ch13_navigation_reuse','platform.launch.py','repo_root:='+str(root),'report:='+str(out/'engine.json')])]
        for name,cmd in commands:
            log=(out/(name+'.log')).open('w');logs.append(log);p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((name,p));S['events'].append({'event':'spawn','name':name,'pid':p.pid})
        rclpy.init();node=Node('ch13_reuse_r2_probe');clock_ns=0;state=None;joints=None;gateway={};platform={};vx=0.;wz=0.;publishing=True;observations=[]
        def on_clock(m):
            nonlocal clock_ns
            clock_ns=ns(m.clock)
        def on_state(m):
            nonlocal state
            state=m;observations.append({'stamp_ns':ns(m.header.stamp),'wall':time.monotonic(),'position':[m.pose.pose.position.x,m.pose.pose.position.y,m.pose.pose.position.z],'velocity':[m.twist.twist.linear.x,m.twist.twist.linear.y,m.twist.twist.linear.z]})
        def on_joints(m):
            nonlocal joints
            joints=m
        def on_gateway(m):
            nonlocal gateway
            gateway=json.loads(m.data)
        def on_platform(m):
            nonlocal platform
            platform=json.loads(m.data)
        node.create_subscription(Clock,'/clock',on_clock,1);node.create_subscription(Odometry,N+'/engine_state',on_state,1);node.create_subscription(JointState,N+'/joint_states',on_joints,1)
        node.create_subscription(String,N+'/gateway/status',on_gateway,1);node.create_subscription(String,N+'/platform/status',on_platform,1)
        pub=node.create_publisher(TwistStamped,N+'/cmd_vel_raw',1)
        def send():
            if not publishing or not clock_ns:return
            m=TwistStamped();set_stamp(m.header.stamp,clock_ns);m.header.frame_id='reuse/nav_base';m.twist.linear.x=vx;m.twist.angular.z=wz;pub.publish(m)
        node.create_timer(.02,send)
        def until(predicate,timeout):
            end=time.monotonic()+timeout
            while time.monotonic()<end:
                rclpy.spin_once(node,timeout_sec=.01)
                if predicate():return True
            return False
        clients={}
        def call(name,request,service=Trigger,timeout=3):
            return service_call(node,name,request,until,clients,service,timeout)
        assert until(lambda:state is not None and clock_ns>2_000_000_000 and gateway.get('ready_for_arm'),a.startup_timeout),'no actual engine state/ready zero command before startup deadline'
        for name in ['platform','gateway']:
            response=call(N+'/'+name+'/arm',Trigger.Request());assert response.success,response.message
        S['events'].append({'event':'armed','clock_ns':clock_ns,'wall':time.monotonic()})
        start_xy=(state.pose.pose.position.x,state.pose.pose.position.y);start_ns=clock_ns;vx=.15
        assert until(lambda:clock_ns-start_ns>=3_000_000_000,10),'forward deadline'
        distance=math.hypot(state.pose.pose.position.x-start_xy[0],state.pose.pose.position.y-start_xy[1]);assert distance>.15,('no actual movement',distance)
        S['forward_distance_m']=distance;vx=0.;zero_ns=clock_ns;zero_wall=time.monotonic()
        assert until(lambda:platform.get('stationary_ready'),8),'actual stop did not settle'
        S['zero_stop_latency_wall_s']=time.monotonic()-zero_wall;assert clock_ns-zero_ns<=5_000_000_000
        def yaw():
            q=state.pose.pose.orientation
            return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        yaw0=yaw();start_ns=clock_ns;wz=.15
        assert until(lambda:clock_ns-start_ns>=3_000_000_000,10),'turn deadline'
        change=abs(math.atan2(math.sin(yaw()-yaw0),math.cos(yaw()-yaw0)));assert change>.15,('no actual turn',change)
        S['turn_angle_rad']=change;wz=0.;turn_zero_ns=clock_ns;turn_zero_wall=time.monotonic()
        assert until(lambda:platform.get('stationary_ready'),8),'actual turn stop did not settle';assert clock_ns-turn_zero_ns<=5_000_000_000
        S['turn_stop_latency_wall_s']=time.monotonic()-turn_zero_wall
        def arm_target(value):
            request=SetParametersAtomically.Request();param=Parameter();param.name='arm_joint1_offset';param.value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE,double_value=value);request.parameters=[param]
            response=call('/ch13_reuse_platform/set_parameters_atomically',request,SetParametersAtomically);assert response.result.successful,response.result.reason
        arm_target(.02);assert until(lambda:joints is not None and joints.position[12]>.01 and platform.get('stationary_ready'),8),'independent arm target not tracked'
        S['arm_joint1_observed_rad']=joints.position[12];arm_target(0.);assert until(lambda:abs(joints.position[12])<.01 and platform.get('stationary_ready'),8)
        vx=.15;start_ns=clock_ns;assert until(lambda:clock_ns-start_ns>=2_000_000_000,8)
        publishing=False;loss_wall=time.monotonic()
        assert until(lambda:gateway.get('mode')=='FAULT',2),'raw loss failed to latch'
        receipt=gateway['source_receipts']['raw']['receipt_wall'];S['raw_expiry_decision_latency_s']=gateway['decision_wall']-receipt;assert S['raw_expiry_decision_latency_s']<=.35
        fault_ns=clock_ns;assert until(lambda:platform.get('stationary_ready'),8),'fault stop failed to settle';assert clock_ns-fault_ns<=5_000_000_000
        publishing=True;vx=.15;assert until(lambda:clock_ns-fault_ns>=1_000_000_000,4);assert gateway['mode']=='FAULT','automatic resume'
        vx=0.;response=call(N+'/platform/shutdown',Trigger.Request());assert response.success,response.message
        platform_process=next(p for name,p in children if name==('launch' if a.launch else 'platform'));platform_process.wait(timeout=8);assert platform_process.returncode==0
        S.update(result='PASS',gateway_final=gateway,platform_final=platform,actual_samples=len(observations),engine=json.loads((out/'engine.json').read_text()))
        assert S['engine']['rx_joined'] and S['engine']['normal_shutdown_requested']
        (out/'ros_observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in observations))
    except BaseException:S['error']=traceback.format_exc()
    finally:
        S['gateway_last']=locals().get('gateway',{});S['platform_last']=locals().get('platform',{})
        if node is not None:node.destroy_node();rclpy.try_shutdown()
        for name,p in reversed(children):
            if p.poll() is None:
                p.send_signal(signal.SIGINT) if name=='launch' else p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
        S['children']=[{'name':name,'pid':p.pid,'exit_code':p.returncode,'reaped':p.poll() is not None} for name,p in children]
        if S['result']=='PASS' and any(p.returncode!=0 for _,p in children):S['result']='FAIL';S['error']='owned child abnormal exit'
        for log in logs:log.close()
        if a.launch:
            output=(out/'launch.log').read_text();pids=re.findall(r'process started with pid \[(\d+)\]',output)
            S['launch_children_pids']=[int(pid) for pid in pids];S['launch_clean_exits']=output.count('process has finished cleanly')
            S['launch_remaining_pids']=[int(pid) for pid in pids if (Path('/proc')/pid/'cmdline').exists()]
            if S['result']=='PASS' and (len(pids)!=3 or S['launch_clean_exits']!=3 or S['launch_remaining_pids'] or 'process has died' in output):
                S['result']='FAIL';S['error']='launch child lifecycle mismatch'
        (out/'probe_summary.json').write_text(json.dumps(S,indent=2)+'\n');print(json.dumps(S,indent=2),flush=True)
    return 0 if S['result']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
