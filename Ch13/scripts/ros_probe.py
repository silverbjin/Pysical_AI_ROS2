#!/usr/bin/env python3
"""Run an owned launch process, observe the real ROS graph, and stop only that process tree."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from ch13_sim_core.contract import load_contract
from ch13_control.common import base_tilt

class Probe(Node):
    def __init__(self):
        super().__init__('ch13_evidence_probe');self.joints=[];self.clocks=[];self.poses=[];self.authorities={};self.commands=[]
        self.create_subscription(JointState,'/joint_states',lambda m:self.joints.append(m),100)
        self.create_subscription(JointState,'/ch13/command/actuators',lambda m:self.commands.append(m),100)
        self.create_subscription(Clock,'/clock',lambda m:self.clocks.append(m.clock.sec+m.clock.nanosec*1e-9),100)
        self.create_subscription(Odometry,'/odom',lambda m:self.poses.append(m),100)
        self.create_subscription(TFMessage,'/tf',self.transforms,100)
        self.create_subscription(TFMessage,'/tf_static',self.transforms,QoSProfile(depth=10,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    def transforms(self,msg,info):
        for t in msg.transforms:self.authorities.setdefault(t.child_frame_id,set()).add(t.header.frame_id)

def run(backend,output,duration=35,probe_factory=Probe,extra_args=None):
    output.parent.mkdir(parents=True,exist_ok=True)
    log=output.with_suffix('.launch.log').open('w')
    process=subprocess.Popen(['ros2','launch','ch13_control','mobile_manipulation.launch.py','backend:='+backend,'enabled:=true','headless:=true']+(extra_args or []),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    rclpy.init();probe=probe_factory();end=time.monotonic()+duration;result={'checks':{},'error':'probe did not complete'}
    try:
        while time.monotonic()<end and process.poll() is None:
            rclpy.spin_once(probe,timeout_sec=.1)
            if hasattr(probe,'sample'):probe.sample()
        c=load_contract();full=all(set(m.name)==set(c.names) and len(m.name)==20 for m in probe.joints)
        stable=len(probe.poses)>20 and all(.38 < m.pose.pose.position.z < .55 and base_tilt(m.pose.pose.orientation) < .15 for m in probe.poses[20:])
        counts={t:probe.count_publishers(t) for t in ('/ch13/command/actuators','/ch13/joint_states_raw','/joint_states','/clock')}
        checks={'twenty_joints':bool(probe.joints) and full,'clock_advances':len(probe.clocks)>5 and probe.clocks[-1]>probe.clocks[0]+1,'single_publishers':all(v==1 for v in counts.values()),'base_stable':stable,'tf_unique':bool(probe.authorities) and all(len(a)==1 for a in probe.authorities.values()),'tf_root_observed':'base_footprint' in probe.authorities and 'tool0' in probe.authorities,'commands_received':len(probe.commands)>20}
        result={'schema_version':1,'backend':backend,'checks':checks,'publisher_counts':counts,'joint_samples':len(probe.joints),'clock_samples':len(probe.clocks),'tf_parents':{k:list(v) for k,v in probe.authorities.items()},'tf_publishers':[e.node_name for e in probe.get_publishers_info_by_topic('/tf')],'tf_per_message_gid':'UNAVAILABLE in installed Jazzy callback metadata; parent uniqueness and graph endpoints checked','last_joint_names':probe.joints[-1].name if probe.joints else [],'last_joint_positions':list(probe.joints[-1].position) if probe.joints else [],'base_samples':[[m.header.stamp.sec+m.header.stamp.nanosec*1e-9,m.pose.pose.position.x,m.pose.pose.position.y,m.pose.pose.position.z,m.pose.pose.orientation.w] for m in probe.poses]}
        if hasattr(probe,'finish'):probe.finish(result)
    except Exception as e:
        result['error']=repr(e)
    finally:
        probe.destroy_node();rclpy.shutdown()
        if process.poll() is None:process.send_signal(signal.SIGINT)
        forced=False
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGTERM);forced=True;process.wait(timeout=5)
        log.close()
        # Launch may exit before its owned Gazebo grandchild. Never touch other process groups.
        leftovers=subprocess.run(['pgrep','-g',str(process.pid)],capture_output=True,text=True).stdout.split()
        if leftovers:
            forced=True
            os.killpg(process.pid,signal.SIGTERM)
            time.sleep(1)
        result['shutdown']={'launch_returncode':process.returncode,'forced_cleanup':forced,'remaining_owned_pids':subprocess.run(['pgrep','-g',str(process.pid)],capture_output=True,text=True).stdout.split()}
    result['checks']['clean_shutdown']=not result['shutdown']['remaining_owned_pids'] and process.returncode==0 and not forced
    result['status']='PASS' if all(result['checks'].values()) else 'FAIL'
    output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('base_samples','tf_parents','grasp_samples')},indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['mujoco','gazebo'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=float,default=35)
    a=p.parse_args();raise SystemExit(run(a.backend,a.output,a.duration))
