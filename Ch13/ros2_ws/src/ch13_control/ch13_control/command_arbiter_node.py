import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from ch13_sim_core.arbiter import CommandArbiter,GroupCommand
from ch13_sim_core.contract import load_contract
from .common import seconds,joint_message,run,sole_publisher_id

def to_command(msg,transport_owner):
    return GroupCommand(tuple(msg.name),np.array(msg.position,dtype=float),seconds(msg.header.stamp),transport_owner)

class ArbiterNode(Node):
    def __init__(self):
        super().__init__('command_arbiter')
        self.arbiter=CommandArbiter(load_contract())
        self.output=self.create_publisher(JointState,'/ch13/command/actuators',10)
        self.status=self.create_publisher(String,'/ch13/status/command',10)
        for group in self.arbiter.contract.groups:
            self.create_subscription(JointState,'/ch13/command/'+group,self.group_callback(group),10)
        self.create_timer(.02,self.tick)
    def group_callback(self,group):
        def callback(msg,info):self.receive(group,msg,info)
        return callback
    def receive(self,group,msg,info):
        try:self.arbiter.update(group,to_command(msg,sole_publisher_id(self.get_publishers_info_by_topic('/ch13/command/'+group))))
        except ValueError as e:self.status.publish(String(data='rejected: '+str(e)))
    def tick(self):
        now=self.get_clock().now()
        r=self.arbiter.resolve(now.nanoseconds*1e-9)
        self.output.publish(joint_message(self.arbiter.contract.names,r.targets,now.to_msg()))
        self.status.publish(String(data=r.status))
def main():run(ArbiterNode)
