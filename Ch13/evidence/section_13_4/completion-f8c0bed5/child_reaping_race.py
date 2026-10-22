"""Controlled Python3.12 pidfd/Popen race; diagnostic, not native acceptance."""
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import time


async def main():
    process = await asyncio.create_subprocess_exec(sys.executable, '-u', '-c',
        'import signal,sys; signal.signal(signal.SIGINT,lambda *_:sys.exit(0)); '
        'print("READY",flush=True); signal.pause()', stdout=asyncio.subprocess.PIPE)
    assert await process.stdout.readline() == b'READY\n'
    os.kill(process.pid, signal.SIGINT)
    # Deliberately hold the parent's event loop at the observed shutdown boundary.
    deadline = time.monotonic()+2.
    while time.monotonic() < deadline:
        state = Path(f'/proc/{process.pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
        if state == 'Z':
            break
        time.sleep(.005)
    assert state == 'Z'
    # Launch also forwards SIGINT to children when its own SIGINT arrives.
    # Popen.send_signal polls/reaps the already exited child before the pidfd callback.
    process.send_signal(signal.SIGINT)
    result = await process.wait()
    print(json.dumps(dict(watcher=type(asyncio.get_child_watcher()).__name__,
                         child_intended_exit=0, reported_returncode=result,
                         zombie_before_next_shutdown_phase=True)))
    assert result == 255, 'diagnostic schedule did not reproduce the observed failure'


asyncio.run(main())
