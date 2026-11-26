import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2_ws/src/ch15_mission'))
from ch15_mission.mission_context import MissionContext, RobotState, ErrorCode, MissionRegistry, steps_for, validate_scenario


class ScenarioTests(unittest.TestCase):
    def test_profiles(self):
        self.assertEqual(steps_for('mock'), ('navigate','detect','approach_stand','pick_retract','return_home','place','verify_finish'))
        self.assertEqual(steps_for('physical_basic'), ('navigate','detect','approach_stand','verify_finish'))
        for name in ('physical_full','unknown'):
            with self.assertRaises(ValueError): steps_for(name)

    def test_context(self):
        c = MissionContext('mission-1')
        self.assertEqual(c.state, RobotState.IDLE)
        self.assertEqual(c.error_code, ErrorCode.NONE)
        self.assertFalse(c.full_mission_success)
        self.assertFalse(c.is_object_grasped)
        self.assertEqual(c.grasp_source, 'UNKNOWN')
        self.assertEqual(MissionContext('mission-2', 'physical_basic').target_object_class, 'upright_cylinder')

    def test_registry(self):
        r = MissionRegistry()
        c = r.start('mission-1', 'mock')
        with self.assertRaises(ValueError): r.start('mission-2', 'mock')
        with self.assertRaises(ValueError): r.advance(c.mission_id, 'navigate')
        r.mark_ready(c.mission_id)
        for step in steps_for('mock'): r.advance(c.mission_id, step)
        r.finish(c.mission_id, RobotState.COMPLETED)
        self.assertEqual(c.state, RobotState.COMPLETED)
        self.assertFalse(c.full_mission_success)
        with self.assertRaises(ValueError): r.finish(c.mission_id, RobotState.COMPLETED)
        with self.assertRaises(ValueError): r.start('mission-1','mock')
        r.start('mission-2','physical_basic')
        with self.assertRaises(ValueError): r.advance('mission-2','pick_retract')
        with self.assertRaises(ValueError): r.finish('mission-2',RobotState.COMPLETED)
        r.finish('mission-2',RobotState.ABORTED)

    def test_scenarios(self):
        files = sorted((ROOT/'scenarios').glob('*.yaml'))
        self.assertEqual(len(files), 11)
        ids = set()
        for p in files:
            row = json.loads(p.read_text()); validate_scenario(row); ids.add(row['fault_id'])
            bad = dict(row, retry_budget=-1)
            with self.assertRaises(ValueError): validate_scenario(bad)
            with self.assertRaises(ValueError): validate_scenario(dict(row,profile='physical_full'))
        self.assertEqual(ids, {'NORMAL'} | {f'F{i:02d}' for i in range(1,11)})

    def test_invalid_context(self):
        for name in ('', '  ', None):
            with self.assertRaises(ValueError): MissionContext(name)
        for battery in (-1,101,float('nan'),True):
            with self.assertRaises(ValueError): MissionContext('x',virtual_battery_pct=battery)

if __name__ == '__main__': unittest.main()
