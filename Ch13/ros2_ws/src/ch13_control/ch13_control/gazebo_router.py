from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from .common import seconds,run,sole_publisher_id
import numpy as np

def route_targets(names,positions,contract):
    from ch13_sim_core.contract import ordered_values
    if len(names)!=20 or set(names)!=set(contract.names):raise ValueError('expected exact twenty joints')
    values=ordered_values(names,positions,contract.names)
    return dict(zip(contract.names,np.clip(values,contract.lower,contract.upper)))

class GazeboRouter(Node):
    def __init__(self):
        super().__init__('gazebo_router')
        from ch13_sim_core.contract import load_contract
        from gz.transport13 import Node as GzNode
        from gz.msgs10.double_pb2 import Double
        self.Double=Double;self.transport=GzNode();self.contract=load_contract();self.last_stamp=-1.;self.owner=None
        self.outputs={n:self.transport.advertise('/ch13/gz/command/'+n,Double) for n in self.contract.names}
        self.status=self.create_publisher(String,'/ch13/status/simulator',10)
        self.create_subscription(JointState,'/ch13/command/actuators',self.command,10)
    def command(self,msg):
        try:
            owner=sole_publisher_id(self.get_publishers_info_by_topic('/ch13/command/actuators'),expected_node='command_arbiter')
            if self.owner is not None and owner!=self.owner:raise ValueError('owner changed; restart router')
            stamp=seconds(msg.header.stamp);now=self.get_clock().now().nanoseconds*1e-9
            if stamp < self.last_stamp or stamp < now-.25 or stamp > now+.05:raise ValueError('stale/future target')
            targets=route_targets(msg.name,msg.position,self.contract)
            self.last_stamp=stamp;self.owner=owner
            for n,v in targets.items():self.outputs[n].publish(self.Double(data=float(v)))
            self.status.publish(String(data='running'))
        except ValueError as e:self.status.publish(String(data='rejected: '+str(e)))
def gazebo_actions(share,description,options):
    from launch.actions import ExecuteProcess
    from launch_ros.actions import Node
    world=options['world'] or str(share/'worlds/mobile_manipulation.sdf')
    gz_args=['gz','sim','-r','-s'] if options['headless'] else ['gz','sim','-r']
    return [ExecuteProcess(cmd=gz_args+[world],output='screen'),
        Node(package='ros_gz_sim',executable='create',arguments=['-world','ch13','-name','ch13_mobile_manipulator','-topic','robot_description','-z','0.468']),
        Node(package='ros_gz_bridge',executable='parameter_bridge',parameters=[{'config_file':str(share/'config/ros_gz_bridge.yaml')}]),
        Node(package='ch13_control',executable='gazebo_router',parameters=[{'use_sim_time':True}])]
def main():run(GazeboRouter)
