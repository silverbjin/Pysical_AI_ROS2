from rclpy.node import Node
from sensor_msgs.msg import JointState
from ch13_sim_core.contract import load_contract
from .common import joint_message,run

class HoldController(Node):
    def __init__(self):
        super().__init__('hold_controller');self.declare_parameter('enabled',False)
        self.declare_parameter('leg_controller','hold')
        self.contract=load_contract()
        groups=[g for g in self.contract.groups if g!='legs' or self.get_parameter('leg_controller').value=='hold']
        self.outputs={g:self.create_publisher(JointState,'/ch13/command/'+g,10) for g in groups}
        self.create_timer(.02,self.tick)
    def tick(self):
        if not self.get_parameter('enabled').value:return
        for g,p in self.outputs.items():
            group=self.contract.groups[g]
            p.publish(joint_message(group.names,group.nominal,self.get_clock().now().to_msg()))
def main():run(HoldController)
