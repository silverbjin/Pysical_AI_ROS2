"""G08 optional clock-reset boundary: actual ROS DDS, synthetic valid sensor envelope.
No physics or locomotion claim. Isolated command topic, no plant connected."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import rclpy
from sensor_msgs.msg import JointState
from g07_shadow_probe import Probe
OUT=Path('/evidence');EXPORT=Path('/reuse/export')
SHA='1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168'
def main():
    c=json.loads((EXPORT/'policy_contract.json').read_text())
    record=dict(xyzw=[0.,0.,0.,1.],angular=[0.,0.,0.],positions=c['nominal'],velocities=[0.]*12,height=.4,linear=[0.,0.,0.],command=[.2,0.,0.])
    log=(OUT/'controller.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','ch14_rl_deployment.rl_controller','--ros-args','-p','use_sim_time:=true','-p','backend:=mujoco','-p','enabled:=true','-p','onnx_path:='+str(EXPORT/'quadruped_policy.onnx'),'-p','contract_path:='+str(EXPORT/'policy_contract.json'),'-p','contract_sha256:='+SHA],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    w=None;targets=[];result={};error=None;forced=False
    try:
        rclpy.init();w=Probe(record,c['joint_names']);w.t=5_000_000_000
        w.create_subscription(JointState,'/rl/joint_targets',lambda m:targets.append(dict(t=m.header.stamp.sec+m.header.stamp.nanosec*1e-9,names=list(m.name),q=list(m.position),receipt=time.monotonic())),100)
        end=time.monotonic()+12
        while time.monotonic()<end:
            if proc.poll() is not None:raise RuntimeError('controller startup failed')
            w.spin(.1)
            if w.imu.get_subscription_count() and w.joints.get_subscription_count() and w.odom.get_subscription_count() and w.cmd.get_subscription_count() and w.rows:break
        else:raise RuntimeError('DDS discovery timeout')
        initial=w.phase('valid',n=40)
        active=[x for x in initial if x['status']=='active']
        assert len(active)>=10 and any(x['observation'][9]>.1 for x in active)
        w.spin(.1)
        baseline=next(x for x in reversed(w.rows) if x['status']=='active')
        first=len(w.rows);first_target=len(targets);previous_time=w.t/1e9
        w.t=2_000_000_000
        w.phase('clock_only',n=24);w.spin(.2)
        reset=w.rows[first:];assert reset, 'no reset statuses'
        assert any('CLOCK_RESET' in x['status'] or 'WALL_SENSOR_TIMEOUT' in x['status'] or 'wall_sensor_timeout' in x['status'] for x in reset)
        assert all(x['status']!='active' and x['inferences']==baseline['inferences'] for x in reset), 'new policy during clock reset'
        held=targets[first_target:]
        assert all(np.allclose(x['q'],baseline['target'],atol=1e-10) for x in held), 'different target during reset'
        assert all(x['t']<previous_time for x in held)
        recovery=w.phase('valid',n=45,command=False)
        new=[x for x in recovery if x['status']=='active']
        assert any(x['status']=='arming' for x in recovery) and len(new)>=10,'no fresh-sensor rearm and recovery'
        assert all(abs(x['observation'][9])<1e-6 for x in new),'pre-reset command leaked'
        assert all(np.isfinite(x['observation']).all() for x in new)
        result=dict(status='MEASUREMENT_PASS',scope='DDS_CLOCK_RESET_SYNTHETIC_SENSORS_NO_PHYSICS',previous_time=previous_time,reset_to_s=2.02,reset_statuses=len(reset),reset_status_names=sorted(set(x['status'] for x in reset)),hold_targets=len(held),new_policy_commands=0,recovery_active=len(new),old_command_cleared=True,arming_after_reset=True,physical_engine='NOT_RUN')
    except BaseException as e:
        error=repr(e);raise
    finally:
        if w:
            (OUT/'status.json').write_text(json.dumps(w.rows)+'\n')
            (OUT/'targets.json').write_text(json.dumps(targets)+'\n')
            w.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        if proc.poll() is None:proc.send_signal(signal.SIGINT)
        try:rc=proc.wait(timeout=10)
        except subprocess.TimeoutExpired:forced=True;os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
        log.close()
        result.update(status='PASS' if result.get('status')=='MEASUREMENT_PASS' and rc==0 and not forced and error is None else 'FAIL',exit_code=rc,forced_cleanup=forced,error=error)
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if error is None:assert result['status']=='PASS',result
if __name__=='__main__':main()
