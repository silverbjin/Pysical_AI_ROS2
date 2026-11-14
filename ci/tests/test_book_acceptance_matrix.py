"""L0-only evidence reconciliation assertions; does not launch ROS/Gazebo/Ch10."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ci"))
from book_acceptance_matrix import CHAPTER_SECTIONS, audit, write_report


class EvidenceMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "ci/book_acceptance_evidence.json").read_text(encoding="utf-8"))
        cls.data = audit(ROOT, cls.registry)

    def test_numbered_guide_count_and_ch10_hold(self):
        self.assertEqual(sum(CHAPTER_SECTIONS.values()), 98)
        self.assertEqual(self.data["numbered_sections"], 98)
        self.assertEqual(len(self.data["rows"]), 98)
        self.assertTrue(self.data["ch10_hold"])
        self.assertEqual(len(self.data["missing_guide_sections"]),
                         sum(not r["exists"] for r in self.data["rows"]))

    def test_guide_count_and_extra_evidence_are_not_runtime_pass(self):
        self.assertEqual(self.data["target_from_issue_118"], 101)
        self.assertFalse(self.data["overall_101_lab_execution_accepted"])
        self.assertEqual(self.data["overall_verdict"], "NOT_READY_FOR_FULL_RUNTIME_ACCEPTANCE")
        self.assertEqual(self.data["unique_guide_documents_including_supporting"],
                         self.data["numbered_guide_files_present"] + len(self.data["supplemental_guides"]))
        self.assertTrue(all(x["classification"] == "SUPPLEMENTAL_GUIDE_NOT_INDEPENDENT_SECTION"
                            for x in self.data["supplemental_guides"]))

    def test_known_failed_and_blocked_sections_cannot_be_promoted(self):
        statuses = {f"{r['chapter']}/{r['section']}": r["status"] for r in self.data["rows"]}
        self.assertEqual(statuses["Ch07/7.7"], "BLOCKED")
        self.assertEqual(statuses["Ch08/8.7"], "FAIL")
        self.assertEqual(statuses["Ch10/10.4"], "HOLD")
        self.assertEqual(statuses["Ch11/11.7"], "SCOPED_PASS")
        self.assertTrue(any(r["status"] == "EVIDENCE_REVIEW_REQUIRED"
                            for r in self.data["rows"]))
        self.assertNotIn("PASS", statuses.values())

    def test_exports_machine_readable_csv_and_unaccepted_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            write_report(self.data, out)
            csv = (out / "acceptance_matrix.csv").read_text(encoding="utf-8-sig")
            report = (out / "SUMMARY.md").read_text(encoding="utf-8")
            record = json.loads((out / "acceptance_matrix.json").read_text(encoding="utf-8"))
            self.assertIn("Ch07,7.7", csv)
            self.assertIn("Ch08,8.7", csv)
            self.assertIn("NOT_READY", report)
            self.assertEqual(record["numbered_sections"], 98)
            self.assertEqual(len(record["rows"]), 98)


if __name__ == "__main__":
    unittest.main()
