"""A dead launch parent does not imply its native engine child has stopped."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys


def test_cleanup_kills_own_descendant_after_parent_exits():
    path = Path(__file__).resolve().parents[1] / 'scripts/probe_sensors_13_4.py'
    spec = importlib.util.spec_from_file_location('sensor_probe', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    child_code = ('import os,signal,time; '
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                  'print(os.getpid(),flush=True); time.sleep(60)')
    parent_code = f'import subprocess,sys; subprocess.Popen([sys.executable,"-c",{child_code!r}])'
    process = subprocess.Popen([sys.executable, '-c', parent_code], start_new_session=True,
                               stdout=subprocess.PIPE, text=True)
    try:
        child_pid = int(process.stdout.readline())
        process.wait(timeout=3)
        report = module.stop_owned_group(process, grace_s=.2)
        assert report['forced_cleanup'] is True
        assert report['residual_live_pids'] == []
        stat = Path(f'/proc/{child_pid}/stat')
        assert not stat.exists() or stat.read_text().split()[2] == 'Z'
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.stdout.close()
