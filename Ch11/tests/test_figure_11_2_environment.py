"""Exercise the real runner's environment without starting a simulator."""
import os
from pathlib import Path
import re
import subprocess
import unittest


CHAPTER = Path(__file__).resolve().parents[1]


@unittest.skipUnless(Path('/opt/ros/jazzy/setup.bash').exists(), 'Requires ROS Jazzy')
class FigureEnvironmentTests(unittest.TestCase):
    def run_environment(self, partition):
        env = os.environ.copy()
        env.pop('GZ_PARTITION', None)
        if partition is not None:
            env['GZ_PARTITION'] = partition
        result = subprocess.run(
            ['bash', str(CHAPTER / 'scripts/run_figure_11_2.sh'), '--show-args'],
            env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        match = re.search(r'^GZ_PARTITION=(\S+)$', result.stdout, re.MULTILINE)
        self.assertIsNotNone(match, 'Runner must report the Gazebo partition inherited by launch')
        return match.group(1), result.stdout

    def test_default_runs_use_distinct_chapter_partitions(self):
        first, _ = self.run_environment(None)
        second, _ = self.run_environment(None)
        self.assertTrue(first.startswith('ch11_figure_11_2_'))
        self.assertNotEqual(first, second)

    def test_explicit_partition_is_preserved_for_external_gazebo_tools(self):
        partition, _ = self.run_environment('ch11_custom_test')
        self.assertEqual(partition, 'ch11_custom_test')


if __name__ == '__main__':
    unittest.main()
