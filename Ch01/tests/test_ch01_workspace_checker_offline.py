"""ROS-free verification that §1.4 workspace inspector is read-only."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_workspace_layout.sh'


class TestWorkspaceChecker(unittest.TestCase):
    def test_reports_new_workspace_without_mutating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'ws'
            (work / 'src').mkdir(parents=True)
            run = subprocess.run(['bash', str(SCRIPT), str(work)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('src=present', run.stdout)
            self.assertIn('build=absent', run.stdout)
            self.assertEqual(sorted(x.name for x in work.iterdir()), ['src'])

    def test_refuses_relative_path(self):
        run = subprocess.run(['bash', str(SCRIPT), 'relative_ws'],
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn('absolute workspace path', run.stderr)

    def test_refuses_missing_src(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = subprocess.run(['bash', str(SCRIPT), tmp],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)


if __name__ == '__main__':
    unittest.main()
