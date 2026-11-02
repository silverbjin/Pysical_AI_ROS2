"""Actual DDS service discovery must keep the probe's command timer alive."""
from pathlib import Path
import importlib.util,time,unittest
ROS=importlib.util.find_spec('rclpy') is not None
@unittest.skipUnless(ROS,'requires Jazzy')
class ProbeServiceWaitTests(unittest.TestCase):
 def test_service_discovery_spins_command_timer(self):
  import rclpy
  from rclpy.node import Node
  from std_srvs.srv import Trigger
  path=Path(__file__).resolve().parents[5]/'Ch13/scripts/reuse_13_5/run_r2_probe.py'
  spec=importlib.util.spec_from_file_location('r2_acceptance_probe',path);probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
  rclpy.init();node=Node('reuse_delayed_service_probe');ticks=[];service=[]
  node.create_timer(.02,lambda:ticks.append(time.monotonic()))
  def reply(request,response):response.success=True;return response
  def create():
   if not service:service.append(node.create_service(Trigger,'/ch13/reuse/probe_delayed_service',reply))
  node.create_timer(.12,create)
  def until(predicate,timeout):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    rclpy.spin_once(node,timeout_sec=.01)
    if predicate():return True
   return False
  try:
   response=probe.service_call(node,'/ch13/reuse/probe_delayed_service',Trigger.Request(),until,{},timeout=1.)
   self.assertTrue(response.success);self.assertGreaterEqual(len(ticks),3)
  finally:node.destroy_node();rclpy.shutdown()
if __name__=='__main__':unittest.main()
