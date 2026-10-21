"""11.7 deterministic exploration safety and end-to-end configuration contracts."""
import importlib
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/my_quadruped_bot'
sys.path.insert(0, str(PKG))


class ExplorationTests(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module('my_quadruped_bot.mission.exploration_core')
        except ModuleNotFoundError:
            self.fail('Missing exploration state machine')
        self.e = self.m.ExplorerCore(seed=3, duration=30)
        self.clear = self.m.ScanSummary(True, 5, 4, 4, 4)

    def test_no_readiness_or_scan_means_no_motion(self):
        self.assertEqual(self.e.step(0, False, None, (0,0,0)), (0,0))
        self.assertEqual(self.e.state, 'WAITING')

    def test_clear_path_advances_at_low_bounded_speed(self):
        self.e.step(0, True, self.clear, (0,0,0))
        vx, wz = self.e.step(1, True, self.clear, (.05,0,0))
        self.assertTrue(0 < vx <= .05)
        self.assertEqual(wz, 0)

    def test_close_front_turns_towards_more_space_then_needs_yaw_progress(self):
        near = self.m.ScanSummary(True, .7, 3, 1, .7)
        self.e.step(0, True, near, (0,0,0))
        vx, wz = self.e.step(1, True, near, (0,0,.1))
        self.assertEqual(vx, 0)
        self.assertGreater(wz, 0)
        self.e.step(14, True, near, (0,0,.1))
        self.assertEqual(self.e.state, 'BLOCKED')

    def test_obstacle_in_swept_radius_blocks_rotation(self):
        near = self.m.ScanSummary(True, .7, 3, .3, .3)
        self.assertEqual(self.e.step(0, True, near, (0,0,0)), (0,0))
        self.assertEqual(self.e.state, 'BLOCKED')

    def test_close_side_obstacle_blocks_forward_swept_body(self):
        near = self.m.ScanSummary(True, 5, .3, 4, .3)
        self.assertEqual(self.e.step(0, True, near, (0,0,0)), (0,0))
        self.assertEqual(self.e.state, 'BLOCKED')

    def test_sensor_loss_stops_even_during_turn(self):
        near = self.m.ScanSummary(True, .7, 3, 1, .7)
        self.e.step(0, True, near, (0,0,0))
        self.assertEqual(self.e.step(1, False, None, (0,0,0)), (0,0))

    def test_deadline_finishes_with_zero_command(self):
        self.e.step(0, True, self.clear, (0,0,0))
        self.assertEqual(self.e.step(31, True, self.clear, (1,0,0)), (0,0))
        self.assertEqual(self.e.state, 'FINISHED')

    def test_stuck_forward_does_not_continue_indefinitely(self):
        self.e.step(0, True, self.clear, (0,0,0))
        self.e.step(9, True, self.clear, (0,0,0))
        self.assertNotEqual(self.e.state, 'FORWARD')

    def test_real_angles_not_array_midpoint_define_front(self):
        # 0..359 degrees: +X is at index 0, not len/2.
        ranges = [5.0]*360
        ranges[0] = .7
        s = self.m.summarize_scan(ranges, 0, math.pi/180, .1, 10)
        self.assertTrue(s.valid)
        self.assertEqual(s.front, .7)

    def test_nan_partial_fov_unknown_but_positive_infinity_is_no_hit(self):
        self.assertTrue(self.m.summarize_scan([math.inf]*360, -math.pi, math.pi/180,.1,10).valid)
        ranges=[5.0]*360; ranges[20]=math.nan
        self.assertFalse(self.m.summarize_scan(ranges,-math.pi,math.pi/180,.1,10).valid)
        self.assertFalse(self.m.summarize_scan([5.0]*60,-.5,math.pi/180,.1,10).valid)

    def test_watchdog_rejects_stale_and_nonfinite_commands(self):
        w = self.m.CommandWatchdog(timeout=.5)
        self.assertEqual(w.value(0), (0,0,0))
        w.receive((.1,0,0), 0)
        self.assertEqual(w.value(.1), (.1,0,0))
        self.assertEqual(w.value(.6), (0,0,0))
        w.receive((math.nan,0,0), .7)
        self.assertEqual(w.value(.8), (0,0,0))


class MappingProjectAssetsTests(unittest.TestCase):
    def test_world_has_four_boundaries_and_local_sensor_systems(self):
        path = PKG/'worlds/maze_room.sdf'
        self.assertTrue(path.exists(), 'Missing complete offline maze')
        root = ET.parse(path).getroot()
        w = root.find('world')
        models={m.get('name') for m in w.findall('model')}
        self.assertTrue({'wall_north','wall_south','wall_east','wall_west'} <= models)
        self.assertGreaterEqual(len(models), 8)
        self.assertFalse(w.findall('include'), 'No network Fuel dependency for lab')
        plugins={p.get('filename') for p in w.findall('plugin')}
        self.assertTrue({'gz-sim-sensors-system','gz-sim-imu-system','gz-sim-scene-broadcaster-system'} <= plugins)

    def test_total_launch_avoids_timer_delays_and_duplicate_localization(self):
        path=PKG/'launch/mapping_total.launch.py'
        self.assertTrue(path.exists(), 'Missing integrated mapping launch')
        text=path.read_text()
        self.assertNotIn('TimerAction', text)
        self.assertIn('SLAM_simulation.launch.py',text)
        self.assertNotIn("'localization.launch.py'", text)
        self.assertIn('start_explorer',text)

    def test_controller_enforces_watchdog(self):
        text=(PKG/'my_quadruped_bot/trot_controllerFSM.py').read_text()
        self.assertIn('CommandWatchdog',text)
        self.assertIn('command_watchdog.value',text)


class ControllerWatchdogRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('rclpy'), 'Requires ROS Python')
    def test_actual_controller_clears_expired_velocity(self):
        import rclpy
        from geometry_msgs.msg import Twist
        from my_quadruped_bot.trot_controllerFSM import TrotControllerNode
        rclpy.init()
        node=TrotControllerNode()
        try:
            msg=Twist();msg.linear.x=.05
            node.cmd_vel_callback(msg)
            node.current_vel_x=.05
            node.command_watchdog.stamp=time.monotonic()-1
            node.timer_callback()
            node.timer_callback()
            self.assertEqual(node.target_vel_x,0)
            self.assertEqual(node.current_vel_x,0)
        finally:
            node.destroy_node()
            rclpy.shutdown()


class SavedMapTests(unittest.TestCase):
    def setUp(self):
        self.m = importlib.import_module('my_quadruped_bot.mission.map_artifacts')

    def test_p5_keeps_whitespace_valued_first_pixel(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.pgm'
            p.write_bytes(b'P5\n# comment\n2 2\n255\n'+bytes([32,0,254,205]))
            width,height,pixels=self.m.read_pgm(p)
            self.assertEqual((width,height),(2,2))
            self.assertEqual(pixels,bytes([32,0,254,205]))

    def test_truncated_pgm_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.pgm';p.write_bytes(b'P5\n2 2\n255\n'+bytes([0]))
            with self.assertRaises(ValueError): self.m.read_pgm(p)

    def test_yaml_and_image_statistics_do_not_claim_accuracy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'map.pgm').write_bytes(b'P5\n2 2\n255\n'+bytes([0,254,205,254]))
            (p/'map.yaml').write_text('image: map.pgm\nresolution: 0.05\norigin: [-1, -2, 0]\nmode: trinary\n')
            r=self.m.analyze_map(p/'map.yaml')
            self.assertEqual(r['pixel_counts']['free_light'],2)
            self.assertFalse(r['quality_verified'])
            self.assertAlmostEqual(r['bounds_area_m2'],.01)

    def test_malformed_yaml_has_controlled_value_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.yaml';p.write_text('image: [')
            with self.assertRaises(ValueError): self.m.analyze_map(p)


if __name__ == '__main__':
    unittest.main()
