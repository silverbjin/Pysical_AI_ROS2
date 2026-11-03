from pathlib import Path
import importlib.util,sys,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
@unittest.skipUnless(importlib.util.find_spec('rclpy'),'requires ROS serialization')
class GatewayValidationTests(unittest.TestCase):
 def test_nonfinite_future_command_faults_before_ordering_wait(self):
  import rclpy
  from rclpy.serialization import serialize_message
  from geometry_msgs.msg import TwistStamped
  from std_msgs.msg import String
  from ch13_navigation_reuse.command_gateway import CommandGateway,set_stamp
  rclpy.init();node=CommandGateway();wall=time.monotonic();node.guard.clock(2_000_000_000,wall,'clock');m=TwistStamped();set_stamp(m.header.stamp,2_040_000_000);m.header.frame_id='reuse/nav_base';m.twist.linear.x=float('nan');packet='r2v1|raw|'+'01'*16+'|'+'02'*16+'|'+str(round(wall*1e9))+'|0|'+serialize_message(m).hex()
  try:node.on_packet(String(data=packet));self.assertEqual(node.guard.mode,'FAULT');self.assertEqual(node.guard.fault,'INVALID_COMMAND')
  finally:node.destroy_node();rclpy.shutdown()
