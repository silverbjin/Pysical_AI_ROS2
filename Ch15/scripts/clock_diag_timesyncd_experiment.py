#!/usr/bin/env python3
"""Approved R10 single-variable experiment. No permanent service or clock changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

SERVICE = "systemd-timesyncd.service"
TRACE_PIN = "bafcf08b2c9072467009c6f232242d74eca8a767"
TRACE_SHA = "e64e6898fa0a71acffc90761d13bce05b729af4623418f0779a4d00e54a2a9eb"
TRACE_URL = f"https://raw.githubusercontent.com/silverbjin/Pysical_AI_ROS2/{TRACE_PIN}/Ch15/scripts/clock_diag_writer_trace.sh"
RESTORE_AFTER = 360
TRACE_LIMIT = 225


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)


def stamp():
    return dict(raw_ns=raw(), mono_ns=time.monotonic_ns(), realtime_ns=time.time_ns())


def append(path, obj):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class Experiment:
    def __init__(self, out):
        self.out = out
        self.unit = "ch15-clock-restore-" + uuid.uuid4().hex
        self.timer = self.unit + ".timer"
        self.original = None
        self.armed = False
        self.restore_needed = False
        self.child = None
        self.interrupted = False
        self.result = {"status": "EXPERIMENT_INCOMPLETE", "owner_acceptance": False,
                       "timer": self.timer, "restore": "NOT_NEEDED",
                       "timer_cleanup": "NOT_ARMED", "experiment": "NOT_RUN"}

    def note(self, message):
        print(message, flush=True)
        append(self.out / "events.jsonl", dict(stamp(), message=message))

    def cmd(self, args, timeout=15, check=True):
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            append(self.out / "commands.jsonl", dict(stamp(), args=args, rc=p.returncode,
                   stdout=p.stdout, stderr=p.stderr))
        except subprocess.TimeoutExpired:
            append(self.out / "commands.jsonl", dict(stamp(), args=args, error="TIMEOUT"))
            raise
        if check and p.returncode:
            raise RuntimeError(f"COMMAND_FAILED {args[:4]} rc={p.returncode}")
        return p

    def state(self, tag):
        p = self.cmd(["systemctl", "show", SERVICE, "--no-pager",
                      "-p", "LoadState", "-p", "ActiveState", "-p", "SubState",
                      "-p", "UnitFileState", "-p", "MainPID", "-p", "FragmentPath"])
        d = dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)
        if not {"LoadState", "ActiveState", "SubState", "UnitFileState", "MainPID"} <= d.keys():
            raise RuntimeError("SERVICE_STATE_INCOMPLETE")
        append(self.out / "service-state.jsonl", dict(stamp(), phase=tag, **d))
        return d

    def snapshot(self, tag):
        # Diagnostic only: no PID signal, no package installation, no clock write.
        self.cmd(["sudo", "-n", "journalctl", "-u", SERVICE, "-n", "80",
                  "-o", "short-monotonic", "--no-pager"], check=False)
        self.cmd(["ps", "-C", "systemd-timesyncd,chronyd", "-o", "pid,ppid,comm"], check=False)
        self.cmd(["systemctl", "list-timers", "--all", "ch15-clock-restore-*", "--no-pager"], check=False)
        self.note("SNAPSHOT_" + tag)

    def preflight(self):
        self.original = self.state("before")
        if (self.original["LoadState"], self.original["ActiveState"], self.original["SubState"]) != ("loaded", "active", "running"):
            raise RuntimeError("PRECONDITION_SERVICE_NOT_ACTIVE_RUNNING")
        if self.original["UnitFileState"] not in ("enabled", "enabled-runtime", "disabled", "static", "indirect"):
            raise RuntimeError("PRECONDITION_UNIT_STATE_UNSUPPORTED")
        if int(self.original["MainPID"]) <= 0:
            raise RuntimeError("PRECONDITION_NO_MAIN_PID")
        # Abort before stopping the service if tracing or the independent timer is unavailable.
        base = next((p for p in ("/sys/kernel/tracing", "/sys/kernel/debug/tracing")
                     if self.cmd(["sudo", "-n", "test", "-d", p + "/instances"], check=False).returncode == 0), None)
        if not base:
            raise RuntimeError("TRACEFS_NOT_AVAILABLE")
        if not any(self.cmd(["sudo", "-n", "test", "-f", base + "/events/syscalls/sys_enter_" + s + "/enable"],
                            check=False).returncode == 0
                   for s in ("clock_adjtime", "adjtimex", "clock_settime", "settimeofday")):
            raise RuntimeError("TRACEPOINTS_NOT_AVAILABLE")
        self.snapshot("BEFORE")
        self.note("PRECHECK_PASS")

    def arm(self):
        # Independent systemd timer survives terminal/runner loss while this distro is running.
        # Mark potential creation before call; a timeout can leave an armed unit.
        self.result["timer_cleanup"] = "REVIEW_REQUIRED"
        self.cmd(["sudo", "-n", "systemd-run", "--unit=" + self.unit,
                  f"--on-active={RESTORE_AFTER}s", "--timer-property=AccuracySec=1s",
                  "--property=Type=oneshot", "--property=TimeoutStartSec=45s",
                  "--", "/usr/bin/systemctl", "start", SERVICE], timeout=25)
        self.cmd(["systemctl", "is-active", "--quiet", self.timer])
        self.armed = True
        self.note("INDEPENDENT_RESTORE_TIMER_ARMED " + self.timer)

    def stop(self):
        if not self.armed:
            raise RuntimeError("RESTORE_TIMER_NOT_ARMED")
        # Restore even if stop times out or returns nonzero after partially succeeding.
        self.restore_needed = True
        self.cmd(["sudo", "-n", "systemctl", "stop", SERVICE], timeout=25)
        s = self.state("stopped")
        if (s["ActiveState"], s["SubState"], s["MainPID"]) != ("inactive", "dead", "0") or s["UnitFileState"] != self.original["UnitFileState"]:
            raise RuntimeError("STOP_NOT_VERIFIED")
        self.note("SERVICE_STOP_VERIFIED")

    def capture(self, trace):
        home = self.out / "trace-home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home))
        start = raw()
        self.note("TRACE_START raw target=180s; service monitored every 5s")
        with (self.out / "trace-console.log").open("w") as log:
            self.child = subprocess.Popen(["bash", str(trace)], env=env, stdout=log,
                                          stderr=subprocess.STDOUT, process_group=0)
            next_check = start
            next_print = start + 30_000_000_000
            while self.child.poll() is None:
                now = raw()
                if self.interrupted:
                    raise InterruptedError("USER_INTERRUPTED")
                if now-start > TRACE_LIMIT*10**9:
                    raise TimeoutError("TRACE_RAW_TIMEOUT")
                if now >= next_check:
                    s = self.state("during")
                    if (s["ActiveState"], s["SubState"], s["MainPID"]) != ("inactive", "dead", "0") or s["UnitFileState"] != self.original["UnitFileState"]:
                        raise RuntimeError("SERVICE_NOT_INACTIVE_DURING_CAPTURE")
                    next_check = now + 5_000_000_000
                if now >= next_print:
                    self.note(f"TRACE_PROGRESS raw elapsed={(now-start)//10**9}s")
                    next_print = now + 30_000_000_000
                time.sleep(.25)
            rc = self.child.returncode
            self.child = None
        if rc:
            raise RuntimeError(f"TRACE_FAILED rc={rc}")
        s = self.state("capture-end")
        if (s["ActiveState"], s["SubState"], s["MainPID"]) != ("inactive", "dead", "0") or s["UnitFileState"] != self.original["UnitFileState"]:
            raise RuntimeError("SERVICE_NOT_INACTIVE_AT_CAPTURE_END")
        archives = list(home.glob("ch15-clock-writer.*.tar.gz"))
        if len(archives) != 1:
            raise RuntimeError("TRACE_ARCHIVE_MISSING_OR_AMBIGUOUS")
        a = archives[0]
        side = Path(str(a) + ".sha256")
        if digest(a) != side.read_text().split()[0]:
            raise RuntimeError("TRACE_ARCHIVE_HASH_MISMATCH")
        data = Path(str(a).removesuffix(".tar.gz"))
        samples = [json.loads(line) for line in (data / "samples.jsonl").read_text().splitlines()]
        if len(samples) < 100 or (samples[-1]["raw_ns"] - samples[0]["raw_ns"]) < 175*10**9:
            raise RuntimeError("TRACE_COVERAGE_INSUFFICIENT")
        if "exit=0\n" not in (data / "status.txt").read_text():
            raise RuntimeError("TRACE_STATUS_NOT_OK")
        self.result["trace_archive"] = a.relative_to(self.out).as_posix()
        self.result["trace_sha256"] = digest(a)
        self.result["samples"] = len(samples)
        self.result["raw_coverage_s"] = (samples[-1]["raw_ns"] - samples[0]["raw_ns"])/1e9
        self.note("TRACE_COMPLETE_REVIEW_REQUIRED")

    def stop_child(self):
        if self.child is not None:
            try:
                if self.child.poll() is None:
                    os.killpg(self.child.pid, signal.SIGTERM)
                    try:
                        self.child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.child.pid, signal.SIGKILL)
                        self.child.wait(timeout=5)
                        self.result["trace_cleanup"] = "FORCED_KILL_REVIEW_TRACEFS"
                self.child = None
            except Exception as e:
                self.result["trace_cleanup"] = repr(e)

    def restore(self):
        # Restore service before cancelling fail-safe. Do not alter enablement.
        if self.restore_needed:
            try:
                self.note("RESTORE_START")
                self.cmd(["sudo", "-n", "systemctl", "start", SERVICE], timeout=45)
                s = self.state("restored")
                if (s["ActiveState"], s["SubState"]) != ("active", "running") or s["UnitFileState"] != self.original["UnitFileState"]:
                    raise RuntimeError("RESTORE_NOT_VERIFIED")
                self.result["restore"] = "ACTIVE_AND_UNIT_FILE_STATE_MATCH"
                self.note("RESTORE_VERIFIED")
            except Exception as e:
                self.result["restore"] = "FAILED_OR_UNVERIFIED"
                self.result["restore_error"] = repr(e)
                self.note("RESTORE_UNVERIFIED: KEEP_FAILSAFE_TIMER; MANUAL START IF NEEDED")
                return
        if self.result["timer_cleanup"] != "NOT_ARMED":
            try:
                self.cmd(["sudo", "-n", "systemctl", "stop", self.timer], timeout=15, check=False)
                p = self.cmd(["systemctl", "show", self.timer, "-p", "ActiveState", "--value"], check=False)
                if p.stdout.strip() not in ("inactive", "failed"):
                    raise RuntimeError("TIMER_CLEANUP_UNVERIFIED")
                self.result["timer_cleanup"] = "INACTIVE"
            except Exception as e:
                self.result["timer_cleanup"] = "UNVERIFIED"
                self.result["timer_error"] = repr(e)

    def execute(self, trace):
        try:
            self.preflight()
            if self.interrupted:
                raise InterruptedError("USER_INTERRUPTED")
            self.arm()
            if self.interrupted:
                raise InterruptedError("USER_INTERRUPTED")
            self.stop()
            if self.interrupted:
                raise InterruptedError("USER_INTERRUPTED")
            self.capture(trace)
            self.result["experiment"] = "CAPTURE_COMPLETE"
        except BaseException as e:
            self.result["error"] = repr(e)
            self.note("EXPERIMENT_ABORTED " + repr(e))
        finally:
            self.stop_child()
            self.restore()
            try:
                self.snapshot("AFTER")
            except Exception as e:
                self.result["snapshot_error"] = repr(e)
        if (self.result["experiment"] == "CAPTURE_COMPLETE" and
            self.result["restore"] == "ACTIVE_AND_UNIT_FILE_STATE_MATCH" and
            self.result["timer_cleanup"] == "INACTIVE" and not self.interrupted):
            self.result["status"] = "EXPERIMENT_COMPLETE_REVIEW_REQUIRED"
        return self.result


def archive(out):
    files = sorted(p for p in out.rglob("*") if p.is_file() and not p.is_symlink())
    (out / "manifest.sha256").write_text("".join(f"{digest(p)}  {p.relative_to(out).as_posix()}\n" for p in files), encoding="utf-8")
    dest = Path(str(out) + ".tar.gz")
    with tarfile.open(dest, "w:gz") as tf:
        for p in files + [out / "manifest.sha256"]:
            tf.add(p, arcname=p.relative_to(out).as_posix(), recursive=False)
    Path(str(dest)+".sha256").write_text(f"{digest(dest)}  {dest.name}\n", encoding="utf-8")
    print(f"EXPERIMENT_EVIDENCE={dest}\nSHA256={dest}.sha256", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-pin", required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--approved", action="store_true", required=True)
    a = p.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", a.source_pin) or digest(Path(__file__)) != a.source_sha256:
        p.error("SOURCE_PIN_OR_HASH_INVALID")
    if os.geteuid() == 0:
        p.error("Run as normal WSL user, not root.")
    os.umask(0o077)
    out = Path(tempfile.mkdtemp(prefix="ch15-clock-timesyncd.", dir=Path.home()))
    e = Experiment(out)
    def interrupt(_sig, _frame):
        e.interrupted = True
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupt)
    try:
        e.note("APPROVED_SINGLE_VARIABLE_ONLY; stop robot missions before running")
        trace = out / "clock_diag_writer_trace.sh"
        e.cmd(["curl", "-fsSLo", str(trace), "--connect-timeout", "10", "--max-time", "30", TRACE_URL], timeout=35)
        if digest(trace) != TRACE_SHA:
            raise RuntimeError("TRACE_SOURCE_SHA_MISMATCH")
        (out / "source-receipt.json").write_text(json.dumps(dict(source_pin=a.source_pin,
             source_sha256=a.source_sha256, trace_pin=TRACE_PIN, trace_sha256=TRACE_SHA, approved=True), indent=2)+"\n")
        # Authentication occurs before service mutation. Fail closed if it fails.
        subprocess.run(["sudo", "-v"], check=True, timeout=120)
        e.execute(trace)
    except BaseException as exc:
        e.result["error"] = repr(exc)
        e.note("PRECHECK_ABORT " + repr(exc))
    finally:
        (out / "status.json").write_text(json.dumps(e.result, indent=2)+"\n")
        archive(out)
    print(e.result["status"], flush=True)
    if e.result["restore"] == "FAILED_OR_UNVERIFIED":
        print("MANUAL: sudo systemctl start systemd-timesyncd.service", flush=True)
    return 0 if e.result["status"] == "EXPERIMENT_COMPLETE_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
