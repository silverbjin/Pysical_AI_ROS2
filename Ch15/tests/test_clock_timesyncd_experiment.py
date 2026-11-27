import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/clock_diag_timesyncd_experiment.py"
spec = importlib.util.spec_from_file_location("experiment", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Fake(m.Experiment):
    def __init__(self, out, failure=""):
        super().__init__(out)
        self.failure = failure
        self.active = True
        self.calls = []

    def note(self, message):
        self.calls.append(message)

    def cmd(self, args, timeout=15, check=True):
        self.calls.append(tuple(args))
        if args[:4] == ["sudo", "-n", "systemctl", "stop"] and args[-1] == m.SERVICE:
            self.active = False
            if self.failure == "stop":
                raise RuntimeError("partial stop")
        if args[:4] == ["sudo", "-n", "systemctl", "start"]:
            if self.failure == "restore":
                raise RuntimeError("restore failure")
            self.active = True
        if args[:3] == ["systemctl", "is-active", "--quiet"] and self.failure == "guard" and self.armed:
            raise RuntimeError("timer lost")
        if "systemd-run" in args and self.failure == "arm":
            raise RuntimeError("timer failure")
        return subprocess.CompletedProcess(args, 0, "inactive\n", "")

    def state(self, tag):
        return dict(LoadState="loaded", ActiveState="active" if self.active else "inactive",
                    SubState="running" if self.active else "dead", MainPID="12" if self.active else "0",
                    UnitFileState="enabled")

    def capture(self, trace):
        self.calls.append("capture")
        if self.failure == "capture":
            raise RuntimeError("capture failed")
        if self.failure == "interrupt":
            self.interrupted = True
            raise InterruptedError()


class Tests(unittest.TestCase):
    def run_case(self, failure=""):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(Path(d), failure)
            return f, f.execute(Path("unused"))

    def test_success_order(self):
        f, r = self.run_case()
        self.assertEqual(r["status"], "EXPERIMENT_COMPLETE_REVIEW_REQUIRED")
        self.assertTrue(f.active)
        self.assertLess(f.calls.index("PRECHECK_PASS"), f.calls.index("SERVICE_STOP_VERIFIED"))
        self.assertLess(f.calls.index("SERVICE_STOP_VERIFIED"), f.calls.index("capture"))
        self.assertLess(f.calls.index("capture"), f.calls.index("RESTORE_VERIFIED"))
        self.assertEqual(r["timer_cleanup"], "INACTIVE")

    def test_stop_partial_failure_restores(self):
        f, r = self.run_case("stop")
        self.assertTrue(f.active)
        self.assertNotIn("capture", f.calls)
        self.assertEqual(r["restore"], "ACTIVE_AND_UNIT_FILE_STATE_MATCH")
        self.assertEqual(r["status"], "EXPERIMENT_INCOMPLETE")

    def test_capture_failure_restores(self):
        f, r = self.run_case("capture")
        self.assertTrue(f.active)
        self.assertEqual(r["restore"], "ACTIVE_AND_UNIT_FILE_STATE_MATCH")
        self.assertEqual(r["status"], "EXPERIMENT_INCOMPLETE")

    def test_interrupt_restores(self):
        f, r = self.run_case("interrupt")
        self.assertTrue(f.active)
        self.assertEqual(r["restore"], "ACTIVE_AND_UNIT_FILE_STATE_MATCH")
        self.assertEqual(r["status"], "EXPERIMENT_INCOMPLETE")

    def test_restore_failure_keeps_timer(self):
        f, r = self.run_case("restore")
        self.assertEqual(r["restore"], "FAILED_OR_UNVERIFIED")
        self.assertNotIn(("sudo","-n","systemctl","stop",f.timer), f.calls)
        self.assertEqual(r["status"], "EXPERIMENT_INCOMPLETE")

    def test_arm_failure_does_not_stop(self):
        f, r = self.run_case("arm")
        self.assertTrue(f.active)
        self.assertNotIn(("sudo","-n","systemctl","stop",m.SERVICE), f.calls)
        self.assertNotIn("capture", f.calls)

    def test_inactive_precondition_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(Path(d))
            f.active = False
            r = f.execute(Path("unused"))
            self.assertEqual(r["restore"], "NOT_NEEDED")
            self.assertFalse(any(isinstance(x,tuple) and "systemd-run" in x for x in f.calls))

    def test_timer_lost_before_stop_no_mutation(self):
        f, r = self.run_case("guard")
        self.assertTrue(f.active)
        self.assertNotIn(("sudo","-n","systemctl","stop",m.SERVICE), f.calls)
        self.assertEqual(r["status"], "EXPERIMENT_INCOMPLETE")

    def test_restart_during_capture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Fake(Path(d))
            f.original = f.state("before")
            f.armed = True
            with self.assertRaisesRegex(RuntimeError, "SERVICE_NOT_INACTIVE_DURING"):
                f.check_inactive("during")

    def test_archive_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"evidence"
            p.mkdir()
            (p/"status.json").write_text("{}")
            m.archive(p)
            dest = Path(str(p)+".tar.gz")
            self.assertEqual(m.digest(dest), Path(str(dest)+".sha256").read_text().split()[0])
            with tarfile.open(dest) as t:
                self.assertEqual(set(t.getnames()), {"status.json","manifest.sha256"})
                self.assertEqual(t.extractfile("manifest.sha256").read().decode().split()[0],m.digest(p/"status.json"))

if __name__ == "__main__":
    unittest.main()
