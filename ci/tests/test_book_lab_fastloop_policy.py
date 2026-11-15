"""Guard the narrow, inexpensive Book Lab documentation CI boundary.

This test must run without ROS/Gazebo, external pip packages, or network.
It protects against a regression that triggered ~190 Book Lab runs in 4 days.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "book-lab-acceptance.yml"

class BookLabFastLoopContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_no_wide_ros_or_physics_path_triggers(self):
        self.assertNotIn("- 'ci/tests/**'", self.workflow)
        self.assertNotIn("- 'Ch[0-1][0-9]/**'", self.workflow)
        self.assertIn("- 'Ch[0-1][0-9]/docs/**'", self.workflow)
        self.assertIn("- 'Ch[0-1][0-9]/README.md'", self.workflow)
        self.assertIn("- 'Ch13/evidence/**/*.md'", self.workflow)

    def test_only_document_validator_unit_tests_run(self):
        self.assertNotIn("discover -s ci/tests -v", self.workflow)
        self.assertIn("-p test_check_guides.py -v", self.workflow)
        self.assertIn("-p test_book_acceptance_matrix.py -v", self.workflow)
        self.assertIn("-p test_book_lab_fastloop_policy.py -v", self.workflow)
        self.assertNotIn("-p test_ch07_77_target_gate.py", self.workflow)

    def test_manual_chapter_pilots_remain_available(self):
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("ch02-action-pilot:", self.workflow)
        self.assertIn("ch12-mujoco-pilot:", self.workflow)

if __name__ == "__main__":
    unittest.main()
