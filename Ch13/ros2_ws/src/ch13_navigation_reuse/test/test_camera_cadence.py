"""Wall watchdog requires wall-scheduled fresh captures in a slow simulator."""
import unittest
from unittest.mock import Mock,patch
import numpy as np
from ch13_navigation_reuse.sensors import SensorSuite
class CameraCadenceTests(unittest.TestCase):
 def test_slow_sim_scan_is_wall_scheduled_with_original_stamp(self):
  s=SensorSuite(None,None,'free','.');s.scan_pub=Mock();p=Mock()
  for sim,wall in [(2.,10.),(2.002,10.05),(2.004,10.101)]:
   with patch('ch13_navigation_reuse.sensors.time.monotonic',return_value=wall),patch('ch13_navigation_reuse.sensors.ray_scan',return_value=[1.]*181):s.step(p,{'stamp_ns':round(sim*1e9)})
  self.assertEqual(s.scan_pub.publish.call_count,2)
  scan=s.scan_pub.publish.call_args.args[0];self.assertEqual(scan.header.stamp.sec,2);self.assertEqual(scan.header.stamp.nanosec,4_000_000);self.assertAlmostEqual(scan.scan_time,.004,places=6)
 def test_slow_sim_new_photos_keep_original_sim_stamps(self):
  s=SensorSuite(None,None,'free','.');s.camera=Mock();s.next_scan=float('inf');s.node=Mock();s.request_capture=Mock();p=Mock();p.mjData.qpos=np.zeros(27)
  for sim,wall in [(2.,10.),(2.002,10.03),(2.004,10.068)]:
   with patch('ch13_navigation_reuse.sensors.time.monotonic',return_value=wall):s.step(p,{'stamp_ns':round(sim*1e9)})
  self.assertEqual(s.request_capture.call_count,2)
  calls=s.request_capture.call_args_list;self.assertEqual(calls[0].args[1:],(2_000_000_000,10.));self.assertEqual(calls[1].args[1:],(2_004_000_000,10.068))
