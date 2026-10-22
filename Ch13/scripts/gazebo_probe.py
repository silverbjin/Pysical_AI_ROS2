#!/usr/bin/env python3
"""Gazebo-only observations. Never infer Gazebo grasp from MuJoCo results."""
import argparse
from dataclasses import asdict
from pathlib import Path
import numpy as np
from rclpy.time import Time
from tf2_ros import Buffer,TransformListener,TransformException
from tf2_msgs.msg import TFMessage
from ros_gz_interfaces.msg import Contacts
from ch13_sim_core.grasp_metrics import GraspObservation,classify_grasp
from ros_probe import Probe,run

class GazeboProbe(Probe):
    def __init__(self):
        super().__init__();self.cube=None;self.contact_names=[];self.contact_time=-1.;self.cube_time=-1.;self.previous=-1.;self.reference=None;self.observations=[]
        self.buffer=Buffer();self.listener=TransformListener(self.buffer,self)
        self.create_subscription(TFMessage,'/ch13/cube_pose',self.cube_pose,100)
        self.create_subscription(Contacts,'/ch13/cube_contacts',self.contacts,100)
    def cube_pose(self,msg):
        for t in msg.transforms:
            if 'cube' in t.child_frame_id:
                p=t.transform.translation;self.cube=np.array([p.x,p.y,p.z]);self.cube_time=t.header.stamp.sec+t.header.stamp.nanosec*1e-9
    def contacts(self,msg):
        self.contact_time=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        self.contact_names=[c.collision1.name+' '+c.collision2.name for c in msg.contacts]
    def sample(self):
        if not self.clocks or self.cube is None:return
        now=self.clocks[-1]
        if now-self.previous<.019:return
        self.previous=now
        try:transform=self.buffer.lookup_transform('odom','grasp_site',Time())
        except TransformException:return
        p=transform.transform.translation;tool=np.array([p.x,p.y,p.z])
        if self.reference is None:self.reference=self.cube-tool
        fresh=abs(now-self.contact_time)<.05 and abs(now-self.cube_time)<.05
        left=fresh and any('gripper_left' in n for n in self.contact_names)
        right=fresh and any('gripper_right' in n for n in self.contact_names)
        self.observations.append(GraspObservation(now,left,right,float(self.cube[2]-.478),float(np.linalg.norm(self.cube-tool-self.reference))))
    def finish(self,result):
        grasp=classify_grasp(self.observations)
        result['physical_grasp']={'status':('PASS' if grasp.success else 'FAIL') if self.observations else 'UNVERIFIED',**asdict(grasp),'contact_messages_observed':self.contact_time>=0,'cube_pose_observed':self.cube is not None}
        result['grasp_samples']=[asdict(o) for o in self.observations]
        # A limited joint-response check, independent of whether the physical fixture grasp succeeds.
        positions=[dict(zip(m.name,m.position)).get('arm_joint_2',0) for m in self.joints]
        result['checks']['arm_command_response']=bool(positions) and min(positions)<-.10
        from gz.transport13 import Node
        from gz.msgs10.server_control_pb2 import ServerControl
        from gz.msgs10.boolean_pb2 import Boolean
        transport=Node()
        result['gazebo_joint_command_publishers']={n:len(transport.topic_info('/ch13/gz/command/'+n)[0]) for n in self.joints[-1].name} if self.joints else {}
        result['checks']['single_gazebo_joint_command_publishers']=len(result['gazebo_joint_command_publishers'])==20 and all(v==1 for v in result['gazebo_joint_command_publishers'].values())
        ok,response=transport.request('/server_control',ServerControl(stop=True),ServerControl,Boolean,3000)
        result['server_control_ack']=bool(ok and response.data)
        result['checks']['server_control_ack']=result['server_control_ack']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('Ch13/evidence/gazebo/result.json'));p.add_argument('--duration',type=float,default=40)
    a=p.parse_args();raise SystemExit(run('gazebo',a.output,a.duration,GazeboProbe,['fixture_demo:=true']))
