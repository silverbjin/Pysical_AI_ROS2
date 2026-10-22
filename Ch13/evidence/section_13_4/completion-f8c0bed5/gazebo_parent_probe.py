"""Diagnostic ONLY: ordinary-user parent GDB, same product trial and stop RPC.

The inferior can have a separate PGID. Its debugger owner is waited on; this
run is never counted as native acceptance, regardless of the runner verdict.
"""
import os
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path('Ch13/scripts').resolve()))
import run_vision_13_4 as runner
from probe_sensors_13_4 import live_group_pids

root = Path(os.environ['CH13_EGL_EVIDENCE']) / 'gazebo-parent-completion'
original_build = runner.build_launch_command


def command(args, delay):
    result = original_build(args, delay)
    prefix = 'exec ' + shlex.join([sys.executable,
        str(Path('Ch13/scripts/parent_debugger_13_4.py').resolve()),
        '--log', str(root/'parent-gdb.log'), '--'])
    result[2:2] = ['--launch-prefix', prefix, '--launch-prefix-filter', '^gz sim$']
    return result


def owners(process):
    found = []
    for pid in live_group_pids(process.pid):
        try:
            argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
            if any(arg.endswith(b'/parent_debugger_13_4.py') for arg in argv):
                found.append(pid)
        except OSError:
            pass
    return found


runner.build_launch_command = command
runner.owned_gazebo_members = owners
sys.argv = [sys.argv[0], '--engine', 'gazebo', '--scenario', 'tracking',
            '--detector-backend', 'color_fixture', '--trace-enabled',
            '--output-dir', str(root)]
raise SystemExit(runner.main())
