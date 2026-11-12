import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_guides import audit_file, markdown_targets


class MarkdownAuditTests(unittest.TestCase):
    def test_only_relative_markdown_links(self):
        text = "[a](docs/ok.md) [web](https://example.org/test.md) [anchor](#heading) [file](src/run.py)"
        self.assertEqual(list(markdown_targets(text)), ["docs/ok.md"])

    def test_detect_missing_relative_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "README.md"
            p.write_text("[missing](docs/not-here.md)", encoding="utf-8")
            result = audit_file(p, root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Broken Markdown link", result["issues"][0])

    def test_detect_valid_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "ok.md").write_text("ok", encoding="utf-8")
            p = root / "README.md"
            p.write_text("[ok](docs/ok.md)", encoding="utf-8")
            self.assertEqual(audit_file(p, root)["status"], "PASS")

    def test_unclosed_fence_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "README.md"
            p.write_text("intro\n" + chr(96) * 3 + "bash\npwd\n", encoding="utf-8")
            result = audit_file(p, root)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("Unbalanced fenced code block", result["issues"][0])


if __name__ == "__main__":
    unittest.main()
