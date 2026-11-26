"""G08 actual Gazebo witness. Float64 commands have receipt time, not source stamp."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import String,Float64
OUT=Path('/evidence');REUSE=Path('/reuse/export');ROOT=Path('/ch14/vendor/ch11_g08')
SHA='1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168'
CONTRACT=json.loads((REUSE/'policy_contract.json').read_text())
NAMES=CONTRACT['joint_names'];LIMITS=np.array(CONTRACT['joint_limits'])
def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9
class Witness(Node):
    def __init__(self):
        super().__init__('g08_gazebo_witness')
        self.status=[];self.joints=[];self.odom=[];self.imu=[];self.commands={n:[] for n in NAMES}
        self.create_subscription(String,'/rl/controller_status',lambda m:self.status.append(dict(json.loads(m.data),receipt=time.monotonic())),100)
        self.create_subscription(JointState,'/joint_states',lambda m:self.joints.append(dict(t=stamp(m),frame=m.header.frame_id,names=list(m.name),q=list(m.position),dq=list(m.velocity))),qos_profile_sensor_data)
        self.create_subscription(Odometry,'/simulation/odom',lambda m:self.odom.append(dict(t=stamp(m),height=m.pose.pose.position.z,frame=m.header.frame_id,child=m.child_frame_id)),qos_profile_sensor_data)
        self.create_subscription(Imu,'/imu/data_raw',lambda m:self.imu.append(dict(t=stamp(m),frame=m.header.frame_id,xyzw=[m.orientation.x,m.orientation.y,m.orientation.z,m.orientation.w])),qos_profile_sensor_data)
        for n in NAMES:
            self.create_subscription(Float64,f'/model/my_quadruped/joint/{n}/cmd_pos',lambda m,n=n:self.commands[n].append(dict(receipt=time.monotonic(),value=m.data)),100)
        self.cmd=self.create_publisher(Twist,'/cmd_vel',10)
def main():
    owned=[];w=None;error=None;result={};shutdown=[]
    def start(name,cmd):
        log=(OUT/(name+'.log')).open('w');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        owned.append((name,p,log));return p
    def command(cmd,log,timeout=20):
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        (OUT/log).write_text(p.stdout+p.stderr)
        return p
    def spin(duration,send=False):
        start=time.monotonic();last=-1
        while time.monotonic()-start<duration:
            if any(p.poll() is not None for _,p,_ in owned):raise RuntimeError('owned process exited')
            elapsed=time.monotonic()-start
            if send and elapsed<1 and elapsed-last>=.05:
                m=Twist();m.linear.x=.2;w.cmd.publish(m);last=elapsed
            rclpy.spin_once(w,timeout_sec=.01)
    try:
        sys.path.insert(0,str(ROOT))
        from gazebo_description import prepare_description
        urdf=OUT/'prepared.urdf';urdf.write_text(prepare_description(ROOT/'urdf/robot.urdf.xacro'))
        rclpy.init();w=Witness()
        start('gazebo',['gz','sim','-s','-r','-v','4','--headless-rendering',str(ROOT/'worlds/empty_world.sdf')])
        # Wait on the real world create service, not a guessed startup sleep.
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            p=command(['gz','service','-l'],'services.log',5)
            if '/world/my_empty_world/create' in p.stdout:break
            spin(.2)
        else:raise RuntimeError('Gazebo create service unavailable')
        prefix=command(['ros2','pkg','prefix','ros_gz_bridge'],'bridge-prefix.log').stdout.strip()
        start('bridge',[prefix+'/lib/ros_gz_bridge/parameter_bridge','--ros-args','-p','config_file:='+str(ROOT/'config/ros_gz_bridge.yaml')])
        prefix=command(['ros2','pkg','prefix','ros_gz_sim'],'sim-prefix.log').stdout.strip()
        p=command([prefix+'/lib/ros_gz_sim/create','-world','my_empty_world','-file',str(urdf),'-name','my_quadruped','-z','.5'],'spawn.log',30)
        if p.returncode!=0:raise RuntimeError('spawn failed')
        start('rl_controller',[sys.executable,'-m','ch14_rl_deployment.rl_controller','--ros-args','-p','use_sim_time:=true','-p','backend:=gazebo','-p','enabled:=true','-p','onnx_path:='+str(REUSE/'quadruped_policy.onnx'),'-p','contract_path:='+str(REUSE/'policy_contract.json'),'-p','contract_sha256:='+SHA])
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            spin(.1)
            if any(x['status']=='active' for x in w.status):break
        else:raise RuntimeError('no active policy within 90s')
        first=len(w.status);start_t=time.monotonic();spin(8,True);wall=time.monotonic()-start_t
        active=[x for x in w.status[first:] if x['status']=='active']
        assert len(active)>=100,('active',len(active))
        times=np.array([x['sim_time'] for x in active]);assert np.all(np.diff(times)>0)
        rate=(len(times)-1)/(times[-1]-times[0]);assert 35<=rate<=55,rate
        assert all(len(x['observation'])==48 and len(x['target'])==12 and np.isfinite(x['observation']).all() and np.isfinite(x['target']).all() for x in active)
        assert any(x['observation'][9]>.1 for x in active) and abs(active[-1]['observation'][9])<1e-6
        heights=[x['height'] for x in w.odom if times[0]<=x['t']<=times[-1]]
        assert heights and min(heights)>.14
        def ordered(row):
            assert len(row['names'])==len(set(row['names'])) and set(NAMES)<=set(row['names'])
            q=np.array([row['q'][row['names'].index(n)] for n in NAMES]);assert np.isfinite(q).all();return q
        cursors={n:0 for n in NAMES};matched=[];responses=[]
        # Per-joint monotone one-to-one receipt matching in a bounded wall window.
        # Float64 carries no source timestamp; never claim exact time alignment of commands.
        for s in active:
            target=np.array(s['target']);assert np.all(target>=LIMITS[:,0]) and np.all(target<=LIMITS[:,1])
            found={}
            for j,n in enumerate(NAMES):
                rows=w.commands[n];k=cursors[n]
                while k<len(rows) and rows[k]['receipt']<s['receipt']-.1:k+=1
                while k<len(rows) and rows[k]['receipt']<=s['receipt']+.1:
                    if abs(rows[k]['value']-target[j])<=1e-8:found[n]=k;break
                    k+=1
                if n not in found:break
            if len(found)!=12:continue
            for n,k in found.items():cursors[n]=k+1
            t=s['sim_time'];matched.append(dict(t=t,status_receipt=s['receipt'],commands={n:w.commands[n][k] for n,k in found.items()}))
            pre=[x for x in w.joints if t-.06<=x['t']<=t+1e-8];post=[x for x in w.joints if t+.019<=x['t']<=t+.10]
            if pre and post:
                a=ordered(pre[-1]);b=ordered(post[0]);delta=b-a
                responses.append(dict(t=t,pre=pre[-1]['t'],post=post[0]['t'],delta_norm=float(np.linalg.norm(delta)),direction_dot=float((target-a)@delta)))
        (OUT/'matched.json').write_text(json.dumps(matched)+'\n');(OUT/'responses.json').write_text(json.dumps(responses)+'\n')
        assert len(matched)>=100,('matched',len(matched))
        assert len(responses)>=50 and any(x['delta_norm']>1e-5 and x['direction_dot']>1e-8 for x in responses)
        assert len(w.get_publishers_info_by_topic('/clock'))==1
        result=dict(status='MEASUREMENT_PASS',scope='SMOKE_ONLY_GAZEBO',active_samples=len(active),sim_rate_hz=rate,wall_seconds=wall,height_min=min(heights),matched_commands=len(matched),feedback_pairs=len(responses),positive_direction_pairs=sum(x['direction_dot']>1e-8 for x in responses),inference_max_s=max(x['inference_seconds'] for x in active),command_expiry='PASS',command_alignment='per-joint receipt window, no source stamp',locomotion_quality='NOT_ACCEPTED')
    except BaseException as e:
        error=repr(e);raise
    finally:
        # Preserve raw data even on failure. Consumers before server service.
        if w:
            for name in ('status','joints','odom','imu','commands'):
                (OUT/(name+'.json')).write_text(json.dumps(getattr(w,name))+'\n')
            w.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        exits={};forced=[];ack=False
        for name,p,log in reversed(owned):
            if p.poll() is None:
                if name=='gazebo':
                    try:
                        stop=command(['gz','service','-s','/server_control','--reqtype','gz.msgs.ServerControl','--reptype','gz.msgs.Boolean','--timeout','1500','--req','stop: true'],'server-stop.log',5)
                        ack=stop.returncode==0 and 'data: true' in stop.stdout
                    except Exception as e:shutdown.append(dict(name=name,stop_error=str(e)))
                else:p.send_signal(signal.SIGINT)
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                forced.append(name);os.killpg(p.pid,signal.SIGKILL);p.wait()
            exits[name]=p.returncode;shutdown.append(dict(name=name,exit=p.returncode,wall=time.monotonic()));log.close()
        clean=len(exits)==3 and all(v==0 for v in exits.values()) and not forced and ack
        result.update(error=error,exit_codes=exits,forced_cleanup=forced,server_stop_ack=ack,shutdown=shutdown,clean_shutdown=clean,status='PASS' if result.get('status')=='MEASUREMENT_PASS' and clean and error is None else 'FAIL')
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if error is None:assert result['status']=='PASS',result
if __name__=='__main__':main()
