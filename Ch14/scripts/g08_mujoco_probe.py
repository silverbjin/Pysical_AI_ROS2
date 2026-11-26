"""G08 first MuJoCo boundary: independent DDS command/physics witness, no training."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool,String

OUT=Path('/evidence')
REUSE=Path('/reuse/export')
CONTRACT_SHA='1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168'
def stamp(msg):return msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
class Witness(Node):
    def __init__(self):
        super().__init__('g08_independent_witness')
        self.status=[];self.sim=[];self.joints=[];self.targets=[];self.odom=[]
        self.create_subscription(String,'/rl/controller_status',lambda m:self.status.append(json.loads(m.data)),10)
        self.create_subscription(String,'/rl/simulator_status',lambda m:self.sim.append(json.loads(m.data)),10)
        self.create_subscription(JointState,'/joint_states',lambda m:self.joints.append(dict(t=stamp(m),names=list(m.name),q=list(m.position),dq=list(m.velocity))),qos_profile_sensor_data)
        self.create_subscription(JointState,'/rl/joint_targets',lambda m:self.targets.append(dict(t=stamp(m),names=list(m.name),q=list(m.position))),10)
        self.create_subscription(Odometry,'/simulation/odom',lambda m:self.odom.append(dict(t=stamp(m),height=m.pose.pose.position.z)),qos_profile_sensor_data)
        self.cmd=self.create_publisher(Twist,'/cmd_vel',10)
        self.pause=self.create_publisher(Bool,'/rl/pause',10)
def main():
    processes=[];w=None;error=None;report={}
    def start(name,args):
        log=(OUT/(name+'.log')).open('w')
        p=subprocess.Popen([sys.executable,'-m','ch14_rl_deployment.'+name,*args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append((name,p,log))
    def spin(duration,command=False):
        start_t=time.monotonic();last=-1
        while time.monotonic()-start_t<duration:
            if any(p.poll() is not None for _,p,_ in processes):raise RuntimeError('owned process exited')
            elapsed=time.monotonic()-start_t
            if command and elapsed<1 and elapsed-last>=.05:
                m=Twist();m.linear.x=.2;w.cmd.publish(m);last=elapsed
            rclpy.spin_once(w,timeout_sec=.02)
    try:
        rclpy.init();w=Witness()
        start('mujoco_bridge',[])
        start('rl_controller',['--ros-args','-p','use_sim_time:=true','-p','backend:=mujoco','-p','enabled:=true','-p','onnx_path:='+str(REUSE/'quadruped_policy.onnx'),'-p','contract_path:='+str(REUSE/'policy_contract.json'),'-p','contract_sha256:='+CONTRACT_SHA])
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            spin(.1)
            if any(x['status']=='active' for x in w.status):break
        else:raise RuntimeError('no active policy within 90s')
        first=len(w.status);start_t=time.monotonic()
        spin(8,True)
        wall=time.monotonic()-start_t
        active=[x for x in w.status[first:] if x['status']=='active']
        assert len(active)>=100,('active',len(active))
        times=np.array([x['sim_time'] for x in active]);assert np.all(np.diff(times)>0)
        hz=(len(times)-1)/(times[-1]-times[0]);assert 35<=hz<=55,hz
        assert all(len(x['observation'])==48 and len(x['target'])==12 and np.isfinite(x['observation']).all() and np.isfinite(x['target']).all() for x in active)
        assert any(x['observation'][9]>.1 for x in active) and abs(active[-1]['observation'][9])<1e-6
        heights=[x['height'] for x in w.odom if times[0]<=x['t']<=times[-1]]
        assert heights and min(heights)>.14
        names=json.loads((REUSE/'policy_contract.json').read_text())['joint_names']
        lim=np.array(json.loads((REUSE/'policy_contract.json').read_text())['joint_limits'])
        def ordered(row):
            assert len(row['names'])==len(set(row['names'])) and set(names)<=set(row['names'])
            q=np.array([row['q'][row['names'].index(n)] for n in names])
            assert np.isfinite(q).all()
            return q
        matches=[];responses=[]
        # Compare independent DDS target with status at the same simulation stamp,
        # then actual joint feedback before and after it. No target-as-feedback.
        for row in active:
            t=row['sim_time']
            candidates=[m for m in w.targets if abs(m['t']-t)<1e-6]
            if not candidates:continue
            target=ordered(candidates[-1]);assert np.allclose(target,row['target'],atol=1e-8)
            assert np.all(target>=lim[:,0]) and np.all(target<=lim[:,1])
            matches.append(t)
            pre=[j for j in w.joints if t-.06<=j['t']<=t+1e-8]
            post=[j for j in w.joints if t+.019<=j['t']<=t+.10]
            if pre and post:
                q0=ordered(pre[-1]);q1=ordered(post[0]);direction=target-q0;delta=q1-q0
                dot=float(direction@delta)
                responses.append(dict(t=t,pre=pre[-1]['t'],post=post[0]['t'],delta_norm=float(np.linalg.norm(delta)),direction_dot=dot))
        assert len(matches)>=100,('matched DDS commands',len(matches))
        assert len(responses)>=50 and any(x['delta_norm']>1e-5 and x['direction_dot']>1e-8 for x in responses), 'no measured joint response in target direction'
        assert w.sim and max(x['command_count'] for x in w.sim)>0 and not any(x['failed'] for x in w.sim)
        assert len(w.get_publishers_info_by_topic('/clock'))==1
        before=len(w.status);w.pause.publish(Bool(data=True));spin(1.2)
        assert any(x['status']=='wall_sensor_timeout' for x in w.status[before:])
        before=len(w.status);w.pause.publish(Bool(data=False));spin(1.5)
        assert any(x['status']=='active' for x in w.status[before:])
        report=dict(status='MEASUREMENT_PASS',scope='SMOKE_ONLY_MUJOCO_NORMAL_AND_PAUSE',active_samples=len(active),sim_rate_hz=hz,wall_seconds=wall,height_min=min(heights),matched_commands=len(matches),feedback_pairs=len(responses),positive_direction_pairs=sum(x['direction_dot']>1e-8 for x in responses),inference_max_s=max(x['inference_seconds'] for x in active),command_expiry='PASS',pause_resume='PASS',responses=responses,locomotion_quality='NOT_ACCEPTED')
    except BaseException as e:
        error=repr(e);raise
    finally:
        if w:
            for name in ('status','sim','joints','targets','odom'):
                (OUT/(name+'.json')).write_text(json.dumps(getattr(w,name),allow_nan=False)+'\n')
            w.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        exits={};forced=[]
        # Stop command writer before plant; never stop a foreign process.
        for name,p,log in reversed(processes):
            if p.poll() is None:p.send_signal(signal.SIGINT)
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                forced.append(name);os.killpg(p.pid,signal.SIGKILL);p.wait()
            exits[name]=p.returncode;log.close()
        clean=len(exits)==2 and all(v==0 for v in exits.values()) and not forced
        report.update(error=error,exit_codes=exits,forced_cleanup=forced,clean_shutdown=clean,status='PASS' if report.get('status')=='MEASUREMENT_PASS' and clean and error is None else 'FAIL')
        (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        if error is None:assert report['status']=='PASS',report
if __name__=='__main__':main()
