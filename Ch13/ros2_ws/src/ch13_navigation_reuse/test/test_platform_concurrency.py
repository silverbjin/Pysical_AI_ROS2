from pathlib import Path
import importlib.util,sys,threading,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
@unittest.skipUnless(ROS,'requires ROS')
class PlatformConcurrencyTests(unittest.TestCase):
 def test_graph_query_does_not_hold_engine_state_lock(self):
  import rclpy
  from ch13_navigation_reuse.platform_adapter import Platform
  rclpy.init();p=Platform();entered=threading.Event();release=threading.Event();done=threading.Event()
  def graph(topic):entered.set();release.wait(.5);return 1
  p.count_publishers=graph
  first=threading.Thread(target=p.monitor);second=threading.Thread(target=lambda:(p.engine_command(2_000_000_000),done.set()))
  try:
   first.start();self.assertTrue(entered.wait(1.));second.start();self.assertTrue(done.wait(.05),'external graph query held the physics command lock')
  finally:release.set();first.join(1.);second.join(1.);p.destroy_node();rclpy.shutdown()
