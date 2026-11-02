"""Known static educational prior, explicitly separate from actual ray scan."""
import argparse,json,math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
from .scene import layout
from .command_gateway import N
class WorldMap(Node):
 def __init__(self,profile):
  super().__init__('ch13_reuse_world_map');q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL);self.pub=self.create_publisher(OccupancyGrid,N+'/map',q)
  m=OccupancyGrid();m.header.frame_id='reuse/map';m.info.resolution=.05;m.info.width=120;m.info.height=100;m.info.origin.position.x=-2.;m.info.origin.position.y=-2.5;m.info.origin.orientation.w=1.;m.data=[]
  for y in range(100):
   for x in range(120):
    px=-2+(x+.5)*.05;py=-2.5+(y+.5)*.05;occupied=any(abs(px-p[0])<=z[0]+.025 and abs(py-p[1])<=z[1]+.025 for _,p,z in layout(profile));m.data.append(100 if occupied else 0)
  self.pub.publish(m);self.map=m
  self.tf=StaticTransformBroadcaster(self);t=TransformStamped();t.header.frame_id='reuse/map';t.child_frame_id='reuse/odom';t.transform.rotation.w=1.;self.tf.sendTransform(t);self.static=t;self.create_timer(1.,self.republish)
 def republish(self):
  self.pub.publish(self.map);self.tf.sendTransform(self.static) # same static stamp/value, supports late relay consumers
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scene',default='free');a,_=parser.parse_known_args();rclpy.init();n=WorldMap(a.scene)
 try:rclpy.spin(n)
 except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
 finally:n.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
