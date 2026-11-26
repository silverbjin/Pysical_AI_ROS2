"""Test-only publisher of typed DDS observation messages, no actuator."""
import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster
from ch15_interfaces.msg import TargetObservation
from ch15_adapters.qos_profiles import profile
class Fixture(Node):
    def __init__(self):
        super().__init__('g03_target_fixture');self.pub=self.create_publisher(TargetObservation,'/g03/target',profile(10))
        self.tf=StaticTransformBroadcaster(self)
        self.sub=self.create_subscription(String,'/g03/target_command',self.send,profile(10))
    def send(self,msg):
        d=json.loads(msg.data)
        if d.get('tf'):
            t=TransformStamped();t.header.frame_id='map';t.child_frame_id='base_link';t.transform.rotation.w=1.;t.header.stamp=self.get_clock().now().to_msg();self.tf.sendTransform(t);return
        t=TargetObservation();t.header.frame_id=d['frame'];t.header.stamp.sec=d['stamp_ns']//1000000000;t.header.stamp.nanosec=d['stamp_ns']%1000000000
        t.mission_id=d['mission_id'];t.epoch=d['epoch'];t.source='MOCK';t.object_class='red_cube';t.pose_kind='GRASP_POSE';t.valid=True;t.reason=d['case']
        t.target_pose.header=t.header;t.target_pose.pose.position.x=float('nan') if d.get('nonfinite') else 1.;t.target_pose.pose.position.z=.225;t.target_pose.pose.orientation.w=1.
        self.pub.publish(t)
def main():
    rclpy.init();n=Fixture()
    try:rclpy.spin(n)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:n.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
