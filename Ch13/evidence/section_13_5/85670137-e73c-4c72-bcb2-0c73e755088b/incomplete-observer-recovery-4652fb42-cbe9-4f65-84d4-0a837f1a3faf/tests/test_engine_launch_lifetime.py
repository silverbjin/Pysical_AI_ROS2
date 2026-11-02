"""Actual launch parent: engine exit must close helpers without a second signal.

The child processes are owned Python fixtures, never a physical-engine result.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest
import run_navigation_13_5 as runner


def test_parent_wait_observes_exit_without_sending_a_signal():
    assert hasattr(runner,'wait_launch_event_exit'),'launch event completion wait missing'
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.05)'])
    report=runner.wait_launch_event_exit(process,timeout_s=2.)
    assert report['confirmed'] is True and report['returncode']==0 and report['signal_sent'] is False


def test_parent_wait_timeout_keeps_failed_owner_alive_for_explicit_cleanup():
    assert hasattr(runner,'wait_launch_event_exit'),'launch event completion wait missing'
    process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)'])
    try:
        report=runner.wait_launch_event_exit(process,timeout_s=.02)
        assert report['confirmed'] is False and report['timed_out'] is True
        assert report['signal_sent'] is False and process.poll() is None
    finally:
        process.terminate();process.wait(timeout=2.) # failed owned fixture, never normal-exit proof


def test_navigation_engine_exit_event_finishes_launch_and_helpers(tmp_path):
    launch_file=Path(__file__).resolve().parents[2]/'integrated_robot_description/launch/gazebo.launch.py'
    program=r'''
import importlib.util,sys
from pathlib import Path
from launch import LaunchDescription,LaunchService
from launch.actions import ExecuteProcess
spec=importlib.util.spec_from_file_location('owned_native_launch',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=Path(sys.argv[2]);ready=root/'ready';closed=root/'closed'
engine_code="import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); end=time.monotonic()+3;\nwhile not p.exists() and time.monotonic()<end:time.sleep(.01)\nassert p.exists()"
helper_code="import pathlib,signal,sys,time;\ndef stop(*_):\n pathlib.Path(sys.argv[2]).write_text('closed'); sys.exit(0)\nsignal.signal(signal.SIGINT,stop);pathlib.Path(sys.argv[1]).write_text('ready');\nwhile True:time.sleep(.02)"
original=ExecuteProcess
def fixture_engine(**kwargs):
    kwargs['cmd']=[sys.executable,'-c',engine_code,str(ready)]
    return original(**kwargs)
module.ExecuteProcess=fixture_engine
engine=module.navigation_gazebo_action('unused-owned-world',True)
helper=ExecuteProcess(cmd=[sys.executable,'-c',helper_code,str(ready),str(closed)],name='owned_fixture_helper')
service=LaunchService();service.include_launch_description(LaunchDescription([engine,helper]))
code=service.run();assert code==0 and closed.read_text()=='closed'
print('OWNED_PARENT_AND_HELPER_NORMAL_EXIT')
'''
    with (tmp_path/'launch.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-c',program,str(launch_file),str(tmp_path)],
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        timed_out=False
        try:
            process.wait(timeout=7.)
        except subprocess.TimeoutExpired:
            timed_out=True
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:process.wait(timeout=6.)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3.)
    output=(tmp_path/'launch.log').read_text()
    assert not timed_out,'engine exited but launch parent/helper require an external signal: '+output
    assert process.returncode==0 and 'OWNED_PARENT_AND_HELPER_NORMAL_EXIT' in output,output
    assert not any(word in output for word in ('escalating to','Traceback','failed to terminate'))
