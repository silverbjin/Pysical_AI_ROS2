"""Known static educational prior, explicitly separate from actual ray scan."""
import argparse,json,math,os,time,hashlib
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import String
from std_srvs.srv import Trigger
from .scene import map_layout as layout
from .command_gateway import N,gid
from .wire import decode
from .map_target import TargetMapGate,occupancy_data
class WorldMap(Node):
 def __init__(self,profile,report=None):
  super().__init__('ch13_reuse_world_map');q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL);self.pub=self.create_publisher(OccupancyGrid,N+'/map',q)
  m=OccupancyGrid();m.header.frame_id='reuse/map';m.info.resolution=.05;m.info.width=120;m.info.height=100;m.info.origin.position.x=-2.;m.info.origin.position.y=-2.5;m.info.origin.orientation.w=1.;m.data=[]
  objects=layout(profile);m.data=occupancy_data(objects)
  self.pub.publish(m);self.map=m
  self.map_gate=None;self.report=report
  if (profile=='vision' and os.environ.get('CH13_VALIDATION_PROFILE')=='carry_v1'
      and os.environ.get('CH13_VALIDATION_SCENARIO') in ('level2_obstacles','level3_house')):
   import copy
   self.map_gate=TargetMapGate();self.map_relay=None;self.picked_map=copy.deepcopy(m)
   self.picked_map.data=occupancy_data([g for g in objects if g[0]!='target'])
   self.initial_hash=hashlib.sha256(bytes(m.data)).hexdigest()
   self.picked_hash=hashlib.sha256(bytes(self.picked_map.data)).hexdigest()
   self.create_subscription(String,N+'/ingress/manipulation/map_physical_hold',self.status_packet,1)
   self.create_service(Trigger,N+'/map/target_state',self.target_state)
  self.tf=StaticTransformBroadcaster(self);t=TransformStamped();t.header.frame_id='reuse/map';t.child_frame_id='reuse/odom';t.transform.rotation.w=1.;self.tf.sendTransform(t);self.static=t;self.create_timer(1.,self.republish)
 def republish(self):
  self.pub.publish(self.map);self.tf.sendTransform(self.static) # same static stamp/value, supports late relay consumers
 def status_packet(self,packet):
  try:
   key,message,info=decode(packet.data)
   if key!='map_physical_hold' or not 0<=time.monotonic()-info['receipt_wall']<=.3:return
   if self.map_relay is None:self.map_relay=info['relay_gid']
   if self.map_relay!=info['relay_gid']:
    self.map_gate.fault='MAP_RELAY_OWNER_REPLACED';return
   self.status_message(message,info)
  except (KeyError,TypeError,ValueError):return
 def status_message(self,message,info):
  if self.map_gate is None:return
  try:row=json.loads(message.data)
  except (TypeError,ValueError):return
  if self.map_gate.observe(row,gid(info),info['receipt_wall']):
   self.map=self.picked_map;self.pub.publish(self.map)
 def target_state(self,request,response):
  value=self.map_gate.snapshot();value.update(initial_map_sha256=self.initial_hash,picked_map_sha256=self.picked_hash)
  response.success=value['removed'] and not value['fault'];response.message=json.dumps(value);return response
 def write_evidence(self):
  if self.map_gate is not None and self.report is not None:
   value=self.map_gate.snapshot();value.update(initial_map_sha256=self.initial_hash,picked_map_sha256=self.picked_hash,
       scope='known target occupancy update only; native moving lease remains authoritative')
   with (Path(self.report).parent/'map_lifecycle.json').open('x') as stream:stream.write(json.dumps(value,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--scene',default='free');parser.add_argument('--report');a,_=parser.parse_known_args();rclpy.init();n=WorldMap(a.scene,a.report)
 try:rclpy.spin(n)
 except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
 finally:n.write_evidence();n.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
