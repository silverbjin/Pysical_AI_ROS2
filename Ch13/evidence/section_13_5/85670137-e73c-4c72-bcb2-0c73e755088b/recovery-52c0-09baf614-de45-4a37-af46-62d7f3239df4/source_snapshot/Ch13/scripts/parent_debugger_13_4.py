#!/usr/bin/env python3
"""Diagnostic launch prefix: own a GDB child, capture stack, forward shutdown.

Not a production launcher or a shutdown fix. It changes timing and must never
turn a failing native run into acceptance evidence. No attach, sudo, sysctl,
GUI, auto-loaded scripts or debuginfod downloads are used.
"""
import argparse
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import signal
import subprocess
from threading import Thread


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or os.geteuid() == 0:
        parser.error('explicit command and ordinary non-root user required')
    log_path = Path(args.log).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    events, shutdown = Queue(), Queue()
    previous = {sig: signal.signal(sig, lambda value, _: shutdown.put(value))
                for sig in (signal.SIGINT, signal.SIGTERM)}
    env = dict(os.environ, DEBUGINFOD_URLS='')
    gdb_command = ['gdb', '--quiet', '--nx', '--interpreter=mi2',
                   '-iex', 'set auto-load off', '-iex', 'set debuginfod enabled off',
                   '--args', *command]
    process = None
    code, pending_signal, stopping = 1, None, False
    running, interrupt_requested = False, False
    with log_path.open('x', encoding='utf-8') as log:
        log.write(json.dumps(dict(euid=os.geteuid(), command=gdb_command))+'\n')
        log.flush()
        try:
            process = subprocess.Popen(gdb_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

            def read():
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    events.put(line)
                events.put(None)

            reader = Thread(target=read, name='gdb-mi-reader', daemon=True)
            reader.start()

            def send(command):
                log.write('# MI command: '+command+'\n')
                log.flush()
                process.stdin.write(command+'\n')
                process.stdin.flush()

            send('1-gdb-set pagination off')
            send('2-gdb-set confirm off')
            send('3-gdb-set mi-async on')
            send('4-gdb-set follow-fork-mode child')
            send('5-exec-run')
            while True:
                try:
                    requested = shutdown.get_nowait()
                    if not stopping:
                        pending_signal = signal.Signals(requested).name
                except Empty:
                    pass
                if pending_signal and running and not interrupt_requested:
                    # MI interrupt targets only GDB's own inferior, and works
                    # without delivering SIGINT during debugger initialization.
                    send('89-exec-interrupt --all')
                    interrupt_requested = True
                try:
                    line = events.get(timeout=.05)
                except Empty:
                    if process.poll() is not None:
                        break
                    continue
                if line is None:
                    break
                if line.startswith('*running'):
                    running = True
                elif line.startswith('*stopped'):
                    running, interrupt_requested = False, False
                if '*stopped' in line and 'reason="exited-signalled"' in line:
                    name = re.search(r'signal-name="([A-Z0-9]+)"', line)
                    code = 128+int(getattr(signal, name[1])) if name else 1
                    stopping = True
                    send('99-gdb-exit')
                elif '=thread-group-exited' in line:
                    native = re.search(r'exit-code="([0-7]+)"', line)
                    if native:
                        code = int(native[1], 8)
                    stopping = True
                    send('99-gdb-exit')
                elif '*stopped' in line and pending_signal is not None:
                    send('90-interpreter-exec console "thread apply all bt"')
                elif line.startswith(('90^done', '90^error')) and pending_signal:
                    send('91-interpreter-exec console "signal '+pending_signal+'"')
                    pending_signal = None
            process.wait(timeout=3.)
            reader.join(timeout=2.)
        finally:
            if process is not None and process.poll() is None:
                # Parent GDB owns the inferior; quitting cannot attach to or
                # operate on unrelated processes. No system policy changes.
                try:
                    process.stdin.write('100-gdb-exit\n')
                    process.stdin.flush()
                    process.wait(timeout=3.)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    process.terminate()
                    process.wait(timeout=3.)
            for sig, handler in previous.items():
                signal.signal(sig, handler)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
