"""A real owned runtime child must finish before engine teardown is allowed."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import run_vision_13_4 as runner


def test_owned_runtime_stops_and_joins_before_engine_phase(tmp_path):
    entry = tmp_path/'lib/integrated_robot_runtime/manipulation_node'
    entry.parent.mkdir(parents=True)
    entry.write_text('import os,signal,sys\n'
                     'signal.signal(signal.SIGINT,lambda *_:sys.exit(0))\n'
                     'print(os.getpid(),flush=True)\n'
                     'signal.pause()\n')
    parent = ('import subprocess,sys; '
              f'p=subprocess.Popen([sys.executable,{str(entry)!r}]); '
              'raise SystemExit(p.wait())')
    process = subprocess.Popen([sys.executable, '-c', parent], stdout=subprocess.PIPE,
                               text=True, start_new_session=True)
    try:
        child_pid = int(process.stdout.readline())
        record = runner.stop_owned_runtime_nodes(process)
        assert record['confirmed'] is True
        assert [item['pid'] for item in record['nodes']] == [child_pid]
        assert record['nodes'][0]['executable'] == str(entry)
        process.wait(timeout=3)
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        process.stdout.close()


def test_runtime_stop_waits_for_parent_reaping_not_only_zombie(tmp_path):
    entry = tmp_path/'lib/integrated_robot_runtime/manipulation_node'
    entry.parent.mkdir(parents=True)
    entry.write_text('import os,signal,sys\n'
                     'signal.signal(signal.SIGINT,lambda *_:sys.exit(0))\n'
                     'print(os.getpid(),flush=True)\n'
                     'signal.pause()\n')
    gate = tmp_path/'allow-parent-reap'
    parent = ('import subprocess,sys,time; from pathlib import Path; '
              f'p=subprocess.Popen([sys.executable,{str(entry)!r}]); '
              f'gate=Path({str(gate)!r}); '
              'exec("while not gate.exists(): time.sleep(.01)"); '
              'raise SystemExit(p.wait())')
    process = subprocess.Popen([sys.executable, '-c', parent], stdout=subprocess.PIPE,
                               text=True, start_new_session=True)
    result, errors = [], []
    def stop():
        try:
            result.append(runner.stop_owned_runtime_nodes(process))
        except Exception as exc:
            errors.append(exc)
    thread = threading.Thread(target=stop)
    try:
        child = int(process.stdout.readline())
        thread.start()
        deadline = time.monotonic()+2.
        while time.monotonic() < deadline:
            state = Path(f'/proc/{child}/stat').read_text().rsplit(')', 1)[1].split()[0]
            if state == 'Z':
                break
            time.sleep(.005)
        assert state == 'Z', 'controlled parent must still own the exited child'
        time.sleep(.1)
        assert thread.is_alive() and not result, 'zombie was declared fully stopped before parent reaping'
        gate.touch()
        thread.join(timeout=2.)
        assert not errors and result[0]['confirmed'] is True
        assert not Path(f'/proc/{child}').exists()
        assert process.wait(timeout=3) == 0
    finally:
        gate.touch()
        thread.join(timeout=3.)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        process.stdout.close()
