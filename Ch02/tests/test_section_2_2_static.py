import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def parse(rel):
    path = ROOT / rel
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path)), source

import subprocess
class Section22(unittest.TestCase):
    def test_bash_syntax_and_help(self):
        script = ROOT / "scripts/check_turtlesim_cli.sh"
        self.assertEqual(subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode, 0)
        help_run = subprocess.run(["bash", str(script), "--help"], capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("turtlesim", help_run.stdout)
    def test_contract_is_explicit(self):
        source = (ROOT / "scripts/check_turtlesim_cli.sh").read_text()
        for token in ("/turtlesim", "/turtle1/cmd_vel", "/turtle1/pose", "/spawn", "CONTRACT_PASS", "set -euo pipefail"):
            self.assertIn(token, source)
if __name__ == "__main__": unittest.main()
