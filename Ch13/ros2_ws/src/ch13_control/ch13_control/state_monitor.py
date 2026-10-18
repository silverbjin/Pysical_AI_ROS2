from copy import deepcopy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from ch13_sim_core.contract import load_contract, ordered_values
from .common import seconds,run

class StateValidator:
    def __init__(self):self.contract=load_contract();self.last=-1.
    def validate(self,msg):
        stamp=seconds(msg.header.stamp)
        positions=ordered_values(msg.name,msg.position,self.contract.names)
        velocities=ordered_values(msg.name,msg.velocity,self.contract.names) if msg.velocity else []
        efforts=ordered_values(msg.name,msg.effort,self.contract.names) if msg.effort else []
        if stamp<=self.last:raise ValueError('non advancing timestamp')
        out=deepcopy(msg);out.name=list(self.contract.names);out.position=positions.tolist()
        out.velocity=list(velocities);out.effort=list(efforts);self.last=stamp
        return out

class StateMonitor(Node):
    def __init__(self):
        super().__init__('state_monitor');self.validator=StateValidator()
        self.publisher=self.create_publisher(JointState,'/joint_states',10)
        self.status=self.create_publisher(String,'/ch13/status/state',10)
        self.create_subscription(JointState,'/ch13/joint_states_raw',self.callback,10)
    def callback(self,msg):
        try:self.publisher.publish(self.validator.validate(msg));status='valid'
        except ValueError as e:status='rejected: '+str(e)
        self.status.publish(String(data=status))
def main():run(StateMonitor)
