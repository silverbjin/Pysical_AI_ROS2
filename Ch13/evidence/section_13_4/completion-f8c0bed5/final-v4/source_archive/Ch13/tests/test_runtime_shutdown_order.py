"""A real owned runtime child must finish before engine teardown is allowed."""
import os
from pathlib import Path
import signal
import subprocess
import sys

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
