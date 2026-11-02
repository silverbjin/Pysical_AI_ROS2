from rclpy.node import Node
from sensor_msgs.msg import JointState,Imu
from rosgraph_msgs.msg import Clock
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster
from ch13_sim_core.mujoco_runtime import MujocoRuntime
from .common import seconds,time_msg,joint_message,run,sole_publisher_id

class MujocoBridge(Node):
    def __init__(self):
        super().__init__('mujoco_bridge')
        self.declare_parameter('seed',42);self.runtime=MujocoRuntime();self.runtime.reset(self.get_parameter('seed').value)
        self.raw=self.create_publisher(JointState,'/ch13/joint_states_raw',10)
        self.clock=self.create_publisher(Clock,'/clock',10)
        self.odom=self.create_publisher(Odometry,'/odom',10)
        self.imu=self.create_publisher(Imu,'/imu',10)
        self.status=self.create_publisher(String,'/ch13/status/simulator',10)
        self.tf=TransformBroadcaster(self)
        self.create_subscription(JointState,'/ch13/command/actuators',self.command,10)
        # Wall-clock scheduling: this node is the source of simulated time.
        self.create_timer(.02,self.tick)
    def command(self,msg):
        try:
            sole_publisher_id(self.get_publishers_info_by_topic('/ch13/command/actuators'),expected_node='command_arbiter')
            self.runtime.apply_named_targets(msg.name,msg.position,seconds(msg.header.stamp))
        except ValueError as e:self.status.publish(String(data='rejected: '+str(e)))
    def tick(self):
        self.runtime.step(10);s=self.runtime.snapshot();stamp=time_msg(s.time)
        self.clock.publish(Clock(clock=stamp))
        msg=joint_message(self.runtime.contract.names,s.positions,stamp);msg.velocity=s.velocities.tolist();self.raw.publish(msg)
        odom=Odometry();odom.header.stamp=stamp;odom.header.frame_id='odom';odom.child_frame_id='base_footprint'
        p=odom.pose.pose.position;p.x,p.y,p.z=map(float,s.base_position)
        q=odom.pose.pose.orientation;q.w,q.x,q.y,q.z=map(float,s.base_quaternion)
        v=odom.twist.twist.linear;v.x,v.y,v.z=map(float,s.base_linear_velocity)
        a=odom.twist.twist.angular;a.x,a.y,a.z=map(float,s.base_angular_velocity)
        self.odom.publish(odom)
        imu=Imu();imu.header.stamp=stamp;imu.header.frame_id='base_link';imu.orientation=q;imu.angular_velocity=a
        imu.linear_acceleration_covariance[0]=-1.;self.imu.publish(imu)
        tf=TransformStamped();tf.header=odom.header;tf.child_frame_id=odom.child_frame_id
        tf.transform.translation.x=p.x;tf.transform.translation.y=p.y;tf.transform.translation.z=p.z;tf.transform.rotation=q
        self.tf.sendTransform(tf);self.status.publish(String(data='running'))
    def destroy_node(self):
        self.runtime.close();return super().destroy_node()
def main():run(MujocoBridge)
