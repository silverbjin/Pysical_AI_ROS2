"""Break: CPU samples combine a recycled/non-owned PID or wrong stat columns."""
from pathlib import Path
import sys
import pytest
import os
import subprocess
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def test_owned_process_cpu_columns_and_start_identity(tmp_path):
    path = tmp_path/'11'
    path.mkdir()
    fields = ['S', '10', '50', '50', '0', '-1', '0', '7', '0', '2', '0',
              '40', '10', '0', '0', '20', '0', '3', '0', '123', '4096', '8']
    (path/'stat').write_text('11 (owned worker) '+' '.join(fields))
    assert runner.process_metrics(11, 50, proc_root=tmp_path) == dict(
        pid=11, ppid=10, pgid=50, start_ticks=123, user_ticks=40, system_ticks=10,
        minor_faults=7, major_faults=2, threads=3, resident_pages=8)
    with pytest.raises(RuntimeError, match='ownership'):
        runner.process_metrics(11, 51, proc_root=tmp_path)


def _stat_text(state='S', start=123):
    fields = [state, '10', '50', '50', '0', '-1', '0', '7', '0', '2', '0',
              '40', '10', '0', '0', '20', '0', '3', '0', str(start), '4096', '8']
    return '11 (owned worker) '+' '.join(fields)


def test_actual_owned_exit_is_not_a_privilege_change_or_valid_cpu_sample():
    # Safe subprocess exec, not fork-with-Python-callbacks after NumPy/ROS imports.
    child = subprocess.Popen([sys.executable, '-c', 'import sys;sys.stdin.buffer.read(1)'],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    try:
        assert runner.process_metrics(child.pid, child.pid)['pid'] == child.pid
        child.stdin.write(b'x')
        child.stdin.flush()
        os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT)
        with pytest.raises(ProcessLookupError, match='exited'):
            runner.process_metrics(child.pid, child.pid)
    finally:
        child.stdin.close()
        assert child.wait(timeout=3.) == 0


@pytest.mark.parametrize('change', ['same_exit', 'replacement_exit', 'foreign_live'])
def test_metadata_race_skips_only_same_identity_confirmed_exit(tmp_path, monkeypatch, change):
    path = tmp_path/'11'
    path.mkdir()
    stat = path/'stat'
    stat.write_text(_stat_text())
    original = Path.stat
    uid = os.getuid()
    def ownership_at_read(candidate, *args, **kwargs):
        if candidate == stat:
            if change != 'foreign_live':
                stat.write_text(_stat_text('Z', 124 if change == 'replacement_exit' else 123))
            return SimpleNamespace(st_uid=uid+1)
        return original(candidate, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', ownership_at_read)
    if change == 'same_exit':
        with pytest.raises(ProcessLookupError, match='exited'):
            runner.process_metrics(11, 50, proc_root=tmp_path)
    else:
        with pytest.raises(RuntimeError, match='ownership|identity'):
            runner.process_metrics(11, 50, proc_root=tmp_path)
