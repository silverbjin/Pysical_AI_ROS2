from pathlib import Path
import importlib.util,sys,subprocess,unittest
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy
 from rclpy.node import Node
 from std_srvs.srv import Trigger
@unittest.skipUnless(ROS,'requires Jazzy')
class ProcessCleanupTests(unittest.TestCase):
 def test_gateway_sigterm_has_normal_exit(self):
  p=subprocess.Popen([sys.executable,'-m','ch13_navigation_reuse.command_gateway'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  rclpy.init();n=Node('reuse_shutdown_probe')
  try:
   client=n.create_client(Trigger,'/ch13/reuse/gateway/arm');self.assertTrue(client.wait_for_service(timeout_sec=5.))
   p.terminate();output=p.communicate(timeout=3.)[0];self.assertEqual(p.returncode,0,output)
  finally:
   if p.poll() is None:p.kill();p.wait(timeout=3.)
   n.destroy_node();rclpy.shutdown()
 def test_sigterm_during_constructor_exits_normally(self):
  import os
  code="""
import os,signal,time,rclpy
import ch13_navigation_reuse.command_gateway as gateway
original=gateway.CommandGateway.create_service
def create(self,kind,name,callback,*args,**kwargs):
    service=original(self,kind,name,callback,*args,**kwargs)
    if name.endswith('/gateway/arm'):
        os.kill(os.getpid(),signal.SIGTERM)
        end=time.monotonic()+1
        while rclpy.ok() and time.monotonic()<end:time.sleep(.001)
    return service
gateway.CommandGateway.create_service=create
gateway.main()
"""
  env=dict(os.environ);env['PYTHONPATH']=str(Path(__file__).resolve().parents[1])+os.pathsep+env.get('PYTHONPATH','')
  p=subprocess.run([sys.executable,'-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5.)
  self.assertEqual(p.returncode,0,p.stdout)
@unittest.skipUnless(ROS,'requires Jazzy')
class StartupStampTests(unittest.TestCase):
 def test_no_unstamped_startup_command_before_engine_clock(self):
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
  from ch13_navigation_reuse.command_gateway import CommandGateway
  from geometry_msgs.msg import TwistStamped
  import time
  rclpy.init();g=CommandGateway();n=Node('unstamped_command_probe');seen=[]
  n.create_subscription(TwistStamped,'/ch13/reuse/cmd_vel_safe',lambda m:seen.append(m),1)
  try:
   end=time.monotonic()+.5
   while time.monotonic()<end:rclpy.spin_once(g,timeout_sec=.01);rclpy.spin_once(n,timeout_sec=.01)
   self.assertFalse(seen,'no source clock means no valid stamped command')
  finally:g.destroy_node();n.destroy_node();rclpy.shutdown()
if __name__=='__main__':unittest.main()

