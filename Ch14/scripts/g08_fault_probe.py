"""Actual MuJoCo DDS negative-path test; no repeat normal 8s benchmark."""
import copy,json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,Imu
from std_msgs.msg import String
from std_srvs.srv import Trigger
OUT=Path('/evidence');REUSE=Path('/reuse/export')
SHA='1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168'
def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9
class Witness(Node):
    def __init__(self):
        super().__init__('g08_fault_witness')
        self.status=[];self.targets=[];self.imu=[];self.bad=False;self.sim=[]
        self.relay=self.create_publisher(Imu,'/g08/test/imu',qos_profile_sensor_data)
        self.create_subscription(Imu,'/imu/data_raw',self.on_imu,qos_profile_sensor_data)
        self.create_subscription(String,'/rl/controller_status',lambda m:self.status.append(dict(json.loads(m.data),receipt=time.monotonic())),100)
        self.create_subscription(String,'/rl/simulator_status',lambda m:self.sim.append(json.loads(m.data)),10)
        self.create_subscription(JointState,'/rl/joint_targets',lambda m:self.targets.append(dict(t=stamp(m),receipt=time.monotonic(),names=list(m.name),q=list(m.position))),100)
        self.rearm=self.create_client(Trigger,'/rl/rearm')
        self.overrun=self.create_client(Trigger,'/g08/test/overrun_once')
    def on_imu(self,m):
        self.imu.append(dict(t=stamp(m),source_frame=m.header.frame_id,injected=self.bad))
        if self.bad:
            m=copy.deepcopy(m);m.header.frame_id='G08_INVALID_FRAME_TEST'
        self.relay.publish(m)
def main():
    owned=[];w=None;checks={};error=None;exits={};forced=[]
    def start(name,cmd):
        log=(OUT/(name+'.log')).open('w');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);owned.append((name,p,log));return p
    def stop(name,p,log):
        if p.poll() is None:p.send_signal(signal.SIGINT)
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            forced.append(name);os.killpg(p.pid,signal.SIGKILL);p.wait()
        exits[name]=p.returncode;log.close()
    def spin(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if any(p.poll() is not None for _,p,_ in owned):raise RuntimeError('owned process exited')
            rclpy.spin_once(w,timeout_sec=.01)
    def until(predicate,timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return
            spin(.04)
        raise RuntimeError('predicate timeout')
    def call(client):
        until(lambda:client.service_is_ready(),5)
        future=client.call_async(Trigger.Request())
        until(lambda:future.done(),5)
        return future.result()
    def launch(enabled,name):
        return start(name,[sys.executable,'/ch14/scripts/g08_fault_controller.py','--ros-args','-p','use_sim_time:=true','-p','backend:=mujoco','-p','enabled:='+str(enabled).lower(),'-p','imu_topic:=/g08/test/imu','-p','onnx_path:='+str(REUSE/'quadruped_policy.onnx'),'-p','contract_path:='+str(REUSE/'policy_contract.json'),'-p','contract_sha256:='+SHA])
    try:
        rclpy.init();w=Witness()
        start('plant',[sys.executable,'-m','ch14_rl_deployment.mujoco_bridge'])
        launch(True,'enabled')
        until(lambda:any(s['status']=='active' for s in w.status),45)
        spin(.3)
        # Invalid actual sensor envelope; hold repeats last accepted position only.
        first=len(w.status);w.bad=True
        until(lambda:any(s['status'].startswith('INVALID_INPUT:imu') for s in w.status[first:]))
        fault=next(s for s in w.status[first:] if s['status'].startswith('INVALID_INPUT:imu'))
        spin(.35)
        rows=[s for s in w.status[first:] if s['receipt']>=fault['receipt']]
        assert len(rows)>=5 and all(s['status'].startswith('INVALID_INPUT:imu') for s in rows)
        assert all(s['inferences']==fault['inferences'] and np.allclose(s['target'],fault['target'],atol=1e-10) for s in rows)
        held=[m for m in w.targets if fault['sim_time']<=m['t']<=rows[-1]['sim_time']]
        assert len(held)>=3 and all(np.allclose(m['q'],fault['target'],atol=1e-10) for m in held)
        checks['invalid_imu_hold']=dict(status='PASS',statuses=len(rows),dds_hold=len(held),inferences=fault['inferences'])
        w.bad=False;first=len(w.status)
        until(lambda:any(s['status']=='active' for s in w.status[first:]))
        # Extra graph writer is discovered but sends no actuator data.
        first=len(w.status);foreign=w.create_publisher(JointState,'/rl/joint_targets',10)
        until(lambda:any('command publishers' in s['status'] for s in w.status[first:]))
        fault=next(s for s in w.status[first:] if 'command publishers' in s['status'])
        spin(.3);rows=[s for s in w.status[first:] if s['receipt']>=fault['receipt']]
        assert len(rows)>=5 and all(s['published']==fault['published'] and s['inferences']==fault['inferences'] for s in rows)
        assert not any(m['t']>fault['sim_time']+1e-8 for m in w.targets)
        assert not call(w.rearm).success
        checks['writer_conflict']=dict(status='PASS',statuses=len(rows),published=fault['published'],rearm_rejected=True)
        w.destroy_publisher(foreign);first=len(w.status)
        until(lambda:any(s['status']=='active' for s in w.status[first:]))
        # Explicit rearm restarts the startup ramp with valid physical sensors.
        first=len(w.status);assert call(w.rearm).success
        until(lambda:any(s['status']=='arming' for s in w.status[first:]))
        until(lambda:any(s['status']=='active' for s in w.status[first:]))
        checks['rearm']=dict(status='PASS',arming_then_active=True)
        spin(.3)
        first=len(w.status);assert call(w.overrun).success
        until(lambda:any(s['status']=='inference_overrun' for s in w.status[first:]))
        i=next(i for i in range(first,len(w.status)) if w.status[i]['status']=='inference_overrun')
        over=w.status[i];prev=w.status[i-1]
        spin(.25)
        assert over['inference_seconds']>.02 and over['published']==prev['published'] and over['inferences']==prev['inferences']
        assert np.allclose(over['target'],prev['target'],atol=1e-10)
        assert not any(abs(m['t']-over['sim_time'])<1e-8 for m in w.targets)
        assert any(s['status']=='active' for s in w.status[i+1:])
        checks['overrun']=dict(status='PASS',inference_s=over['inference_seconds'],new_commands=0,recovered=True)
        # Verify disabled controller creates no actuator publisher, not merely no messages.
        name,p,log=owned.pop();stop(name,p,log)
        until(lambda:len(w.get_publishers_info_by_topic('/rl/joint_targets'))==0,10)
        first=len(w.status);target_count=len(w.targets);launch(False,'disabled')
        until(lambda:any(s['status']=='dry_run' for s in w.status[first:]))
        spin(.35);rows=w.status[first:]
        assert all(s['published']==0 and not s['enabled'] for s in rows)
        assert len(w.get_publishers_info_by_topic('/rl/joint_targets'))==0 and len(w.targets)==target_count
        checks['disabled']=dict(status='PASS',statuses=len(rows),graph_command_publishers=0,commands=0)
    except BaseException as e:
        error=repr(e);raise
    finally:
        if w:
            for name in ('status','targets','imu','sim'):
                (OUT/(name+'.json')).write_text(json.dumps(getattr(w,name))+'\n')
            w.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        for name,p,log in reversed(owned):stop(name,p,log)
        clean=len(exits)==3 and all(v==0 for v in exits.values()) and not forced
        result=dict(status='PASS' if error is None and len(checks)==5 and clean else 'FAIL',scope='MUJOCO_ACTUAL_DDS_NEGATIVE_CONTRACT',checks=checks,error=error,exit_codes=exits,forced_cleanup=forced,clean_shutdown=clean,locomotion_quality='NOT_ACCEPTED')
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if error is None:assert result['status']=='PASS',result
if __name__=='__main__':main()
