from rclpy.node import Node
from sensor_msgs.msg import JointState
from ch13_sim_core.contract import load_contract
from .common import joint_message,run

def fixture_targets(nominal,t):
    q=nominal.copy()
    q[13]=-.2*max(0.,min((t-3)/2,1))
    q[18:]=.035 if t<1 else max(0.,.035*(1-(t-1)/1.5))
    return q

class HoldController(Node):
    def __init__(self):
        super().__init__('hold_controller');self.declare_parameter('enabled',False)
        self.declare_parameter('leg_controller','hold')
        self.declare_parameter('fixture_demo',False)
        self.demo_start=None
        self.create_subscription(JointState,'/joint_states',self.state,10)
        self.contract=load_contract()
        groups=[g for g in self.contract.groups if g!='legs' or self.get_parameter('leg_controller').value=='hold']
        self.outputs={g:self.create_publisher(JointState,'/ch13/command/'+g,10) for g in groups}
        self.create_timer(.02,self.tick)
    def state(self,msg):
        if self.demo_start is None:self.demo_start=self.get_clock().now().nanoseconds*1e-9
    def tick(self):
        if not self.get_parameter('enabled').value:return
        now=self.get_clock().now()
        targets=self.contract.nominal
        if self.get_parameter('fixture_demo').value and self.demo_start is not None:
            targets=fixture_targets(targets,now.nanoseconds*1e-9-self.demo_start)
        for g,p in self.outputs.items():
            group=self.contract.groups[g]
            values=[targets[self.contract.names.index(n)] for n in group.names]
            p.publish(joint_message(group.names,values,now.to_msg()))
def main():run(HoldController)
