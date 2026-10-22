"""Use an actual ordinary-user GDB parent; never attach to an existing process."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/parent_debugger_13_4.py'


def test_parent_debugger_propagates_native_exit_not_debugger_exit(tmp_path):
    log = tmp_path/'parent-gdb.log'
    result = subprocess.run([sys.executable, str(SCRIPT), '--log', str(log), '--',
        sys.executable, '-c', 'raise SystemExit(7)'], capture_output=True, text=True, timeout=10.)
    assert result.returncode == 7, result.stderr
    text = log.read_text()
    assert 'thread-group-started' in text and 'exit-code="07"' in text


def test_parent_debugger_collects_stack_then_forwards_shutdown_to_own_child(tmp_path):
    log = tmp_path/'parent-gdb.log'
    child = ('import signal, os; '
             'signal.signal(signal.SIGINT, lambda *_: os._exit(0)); '
             'print("DEBUG_CHILD_READY", flush=True); signal.pause()')
    process = subprocess.Popen([sys.executable, str(SCRIPT), '--log', str(log), '--',
        sys.executable, '-c', child], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)
    try:
        deadline = time.monotonic()+8.
        while time.monotonic() < deadline and process.poll() is None:
            if log.exists() and '\nDEBUG_CHILD_READY\n' in log.read_text():
                break
            time.sleep(.02)
        assert log.exists() and '\nDEBUG_CHILD_READY\n' in log.read_text()
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=8.)
        assert process.returncode == 0, (stdout, stderr, log.read_text())
        text = log.read_text()
        assert 'thread apply all bt' in text and '#0 ' in text
        assert 'signal SIGINT' in text and 'exit-code="0"' in text
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5.)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=3.)
