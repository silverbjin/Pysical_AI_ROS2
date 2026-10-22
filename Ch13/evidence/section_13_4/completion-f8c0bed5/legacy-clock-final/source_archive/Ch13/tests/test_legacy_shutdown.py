"""Legacy runner must expose graceful/forced cleanup, including descendants."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import json

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import run_architecture_13_3 as runner


def test_legacy_stop_records_actual_graceful_exit_and_no_residuals():
    code = ('import signal,sys; '
            'signal.signal(signal.SIGINT,lambda *_:sys.exit(0)); '
            'print("READY",flush=True); signal.pause()')
    process = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        assert process.stdout.readline().strip() == 'READY'
        record = runner.stop(process)
        assert record == dict(forced_cleanup=False, residual_live_pids=[])
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        process.stdout.close()


def test_launch_failure_keeps_original_error_and_cleanup_result(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['run_architecture', '--engine', 'gazebo',
                                     '--output-dir', str(tmp_path)])
    def fail_launch(*args, **kwargs):
        raise OSError('intentional launch failure')
    monkeypatch.setattr(runner.subprocess, 'Popen', fail_launch)
    with pytest.raises(RuntimeError, match='architecture or normal shutdown failed'):
        runner.main()
    result = json.loads((tmp_path/'result.json').read_text())
    assert result['status'] == 'FAIL'
    assert result['runner_error'] == 'intentional launch failure'
    assert result['cleanup'] == []
    assert result['runtime_shutdown'] == result['engine_shutdown'] == 'FAIL'
