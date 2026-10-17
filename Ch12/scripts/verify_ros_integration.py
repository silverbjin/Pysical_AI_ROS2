"""Actual ROS topics -> PPO -> named position commands -> MuJoCo/Gazebo."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import String,Bool


class Probe(Node):
    def __init__(self):
        super().__init__('rl_integration_probe')
        self.records=[];self.heights=[];self.joints=[]
        self.create_subscription(String,'/rl/controller_status',self.status,10)
        self.create_subscription(Odometry,'/simulation/odom',lambda m:self.heights.append(m.pose.pose.position.z),qos_profile_sensor_data)
        self.create_subscription(JointState,'/joint_states',lambda m:self.joints.append(len(m.name)),qos_profile_sensor_data)
        self.cmd=self.create_publisher(Twist,'/cmd_vel',10)
        self.pause=self.create_publisher(Bool,'/rl/pause',10)
    def status(self,msg):
        self.records.append(json.loads(msg.data))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=['mujoco','gazebo'],required=True)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'result.json').unlink(missing_ok=True)
    env=os.environ.copy()
    env['GZ_PARTITION']='ch12_rl_'+str(os.getpid())
    log=args.output/'launch.log'
    handle=log.open('w')
    process=subprocess.Popen(['ros2','launch','quadruped_rl_ros','rl_simulation.launch.py',
        'backend:='+args.backend,'enabled:=true','bundle_path:='+str(args.bundle.resolve())],
        stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    rclpy.init();probe=Probe()
    stop_ack=None;forced=False
    try:
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            rclpy.spin_once(probe,timeout_sec=.05)
            if process.poll() is not None:raise RuntimeError('ROS launch exited during startup')
            if any(r['status']=='active' for r in probe.records):break
        else:raise RuntimeError('No active policy loop within 90 seconds')
        first_active=len(probe.records)-1
        start=time.monotonic();last_send=0
        while time.monotonic()-start<8:
            elapsed=time.monotonic()-start
            if elapsed<1 and elapsed-last_send>.05:
                message=Twist();message.linear.x=.2;probe.cmd.publish(message);last_send=elapsed
            rclpy.spin_once(probe,timeout_sec=.02)
        active=[r for r in probe.records[first_active:] if r['status']=='active']
        measurement_wall=time.monotonic()-start
        assert len(active)>=100,len(active)
        times=np.array([r['sim_time'] for r in active])
        differences=np.diff(times)
        assert np.median(differences)>0
        rate=float((len(times)-1)/(times[-1]-times[0]))
        assert 35<=rate<=55,rate
        assert any(r['observation'][9]>.1 for r in active),'cmd_vel not reflected'
        assert abs(active[-1]['observation'][9])<1e-6,'old command did not expire'
        assert all(np.isfinite(r['observation']).all() and len(r['observation'])==48 for r in active)
        assert all(np.isfinite(r['target']).all() and len(r['target'])==12 for r in active)
        assert probe.heights and min(probe.heights)>.14, min(probe.heights)
        pause_checked=False
        if args.backend=='mujoco':
            probe.pause.publish(Bool(data=True));before=len(probe.records)
            until=time.monotonic()+1.2
            while time.monotonic()<until:rclpy.spin_once(probe,timeout_sec=.03)
            assert any(r['status']=='wall_sensor_timeout' for r in probe.records[before:])
            probe.pause.publish(Bool(data=False));until=time.monotonic()+1
            while time.monotonic()<until:rclpy.spin_once(probe,timeout_sec=.03)
            assert probe.records[-1]['status']=='active'
            pause_checked=True
        report=dict(status='PASS',backend=args.backend,active_samples=len(active),
            policy_sim_time_hz=rate,sim_start=float(times[0]),sim_end=float(times[-1]),
            policy_wall_time_hz=len(active)/measurement_wall,measurement_wall_seconds=measurement_wall,
            height_min=float(min(probe.heights)),height_max=float(max(probe.heights)),
            observation_size=48,joint_name_counts=sorted(set(probe.joints)),
            command_and_timeout='PASS',pause_steady_watchdog=pause_checked,
            inference_seconds_max=max(r['inference_seconds'] for r in active),
            status_counts={s:sum(r['status']==s for r in probe.records) for s in set(r['status'] for r in probe.records)},
            sample=active[-1],limitation='Short smoke model; validates integration, not learned walking proficiency')
        (args.output/'observation.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        probe.destroy_node();rclpy.shutdown()
        if args.backend=='gazebo':
            stop=subprocess.run(['gz','service','-s','/server_control','--reqtype','gz.msgs.ServerControl',
                '--reptype','gz.msgs.Boolean','--timeout','8000','--req','stop: true'],
                env=env,capture_output=True,text=True,timeout=12)
            (args.output/'server_stop.log').write_text(stop.stdout+stop.stderr)
            stop_ack='data: true' in stop.stdout
            time.sleep(2)
        if process.poll() is None:process.send_signal(signal.SIGINT)
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            forced=True;os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
        handle.close()
        text=log.read_text(errors='replace')
        observation=json.loads((args.output/'observation.json').read_text()) if (args.output/'observation.json').exists() else {}
        clean=not forced and 'Traceback' not in text and '[ERROR]' not in text and (stop_ack is not False)
        result=dict(status='PASS' if observation.get('status')=='PASS' and clean else 'FAIL',
            observation=observation,forced_cleanup=forced,shutdown_clean=clean,gazebo_stop_ack=stop_ack,
            launch_exit=process.returncode)
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['status']=='PASS',result
    print(json.dumps({k:v for k,v in result.items() if k!='observation'}))


if __name__=='__main__':main()
