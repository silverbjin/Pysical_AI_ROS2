"""Optional Ch12.8-style policy loop. Does not publish actuator or arm commands."""
import json
from pathlib import Path
import time
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from ch13_sim_core.locomotion_contract import create_policy_core,validate_manifest
from .common import run,joint_message,seconds

def policy_command(core,action,enabled):
    if not enabled:return None
    targets,_=core.process_action(action)
    return core.contract.joint_names,targets

class RLLegController(Node):
    def __init__(self):
        super().__init__('rl_leg_controller')
        self.declare_parameter('enabled',False);self.declare_parameter('bundle_path','')
        self.enabled=self.get_parameter('enabled').value;self.core=create_policy_core();self.model=None
        self.output=self.create_publisher(JointState,'/ch13/command/legs',10)
        self.status=self.create_publisher(String,'/ch13/status/policy',10)
        if self.enabled:
            path=Path(self.get_parameter('bundle_path').value).expanduser().resolve()
            manifest=json.loads((path/'manifest.json').read_text());validate_manifest(manifest)
            model_path=path/'best_model/best_model.zip'
            if not model_path.is_file():raise ValueError('bundle has no model weights: '+str(model_path))
            import torch
            from stable_baselines3 import PPO
            torch.set_num_threads(1)
            self.model=PPO.load(model_path,device='cpu')
            if self.model.observation_space.shape!=(48,) or self.model.action_space.shape!=(12,):raise ValueError('model space mismatch')
        self.create_subscription(JointState,'/joint_states',self.joints,10)
        self.create_subscription(Odometry,'/odom',self.odom,10)
        self.create_timer(.02,self.tick)
    def joints(self,msg):
        try:self.core.update_joints(msg.name,msg.position,msg.velocity,seconds(msg.header.stamp))
        except ValueError as e:self.status.publish(String(data='rejected: '+str(e)))
    def odom(self,msg):
        try:
            q=msg.pose.pose.orientation;a=msg.twist.twist.angular;v=msg.twist.twist.linear;t=seconds(msg.header.stamp)
            self.core.update_imu([q.x,q.y,q.z,q.w],[a.x,a.y,a.z],t)
            self.core.update_velocity([v.x,v.y,v.z],t,'body')
        except ValueError as e:self.status.publish(String(data='rejected: '+str(e)))
    def tick(self):
        if not self.enabled:return
        try:
            now=self.get_clock().now();obs=self.core.observation(now.nanoseconds*1e-9)
            start=time.monotonic();action,_=self.model.predict(obs,deterministic=True)
            if time.monotonic()-start>.02:raise RuntimeError('inference budget exceeded; hold')
            names,targets=policy_command(self.core,action,True)
            self.output.publish(joint_message(names,targets,now.to_msg()))
            self.status.publish(String(data='integration smoke only; not validated walking'))
        except (ValueError,RuntimeError) as e:self.status.publish(String(data=str(e)))
def main():run(RLLegController)
