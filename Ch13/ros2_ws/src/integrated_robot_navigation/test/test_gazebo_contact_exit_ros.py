"""Real contact adapter RPC and owned SIGINT; no Gazebo engine is started."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_srvs.srv import Trigger
from rosgraph_msgs.msg import Clock

from integrated_robot_navigation.scene import materialize_scene


@pytest.mark.parametrize('attempt',range(3))
def test_actual_contact_adapter_replies_then_sigint_closes_cleanly(tmp_path,attempt):
    exercise_exit(tmp_path,attempt)


def test_sigint_keeps_context_alive_until_the_actual_inflight_clock_callback_returns(tmp_path):
    exercise_exit(tmp_path,0,gated=True)


def exercise_exit(tmp_path,attempt,*,gated=False):
    scene=tmp_path/'scene'
    materialize_scene('gazebo','g1',scene,g1_reference_ramp=True,g1_contact_allowance=True)
    source=Path(__file__).resolve().parents[1]
    code='import sys;sys.path.insert(0,'+repr(str(source))+')\n'
    code+='from integrated_robot_navigation.gazebo_contacts import main,GazeboContactJoiner\n'
    if gated:
        # Test-only gate on a real received Clock callback, never an engine.
        # Keep the callback outstanding while the parent delivers owned SIGINT.
        code+='''import rclpy
original=GazeboContactJoiner.observe_clock
def held_clock(self,stamp):
    print('CLOCK_CALLBACK_ENTERED',flush=True)
    sys.stdin.readline()
    assert rclpy.ok(),'context invalidated before the outstanding callback returned'
    original(self,stamp)
    print('CLOCK_CALLBACK_RETURNED_VALID_CONTEXT',flush=True)
GazeboContactJoiner.observe_clock=held_clock
'''
    code+='main(args='+repr(['--ros-args','-p','scene_dir:='+str(scene)])+')\n'
    code+='print("NORMAL_CONTACT_EXIT",flush=True)\n'
    command=[sys.executable,'-c',code]
    context=Context();rclpy.init(context=context)
    peer=Node('contact_exit_peer',context=context)
    executor=SingleThreadedExecutor(context=context);executor.add_node(peer)
    client=peer.create_client(Trigger,'/navigation/stop_native_sensors')
    process=None
    stdout_path,stderr_path=tmp_path/'stdout.log',tmp_path/'stderr.log'
    try:
        with stdout_path.open('x') as out,stderr_path.open('x') as err:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True)
            assert client.wait_for_service(timeout_sec=5.), 'actual contact adapter service missing'
            if attempt==0:
                diagnostic=peer.create_client(Trigger,'/gazebo_contact_adapter/report')
                assert diagnostic.wait_for_service(timeout_sec=2.)
                snapshot=diagnostic.call_async(Trigger.Request());until=time.monotonic()+2.
                while not snapshot.done() and time.monotonic()<until:executor.spin_once(timeout_sec=.01)
                assert snapshot.done() and snapshot.result().success
                boundary=json.loads(snapshot.result().message)
                assert boundary['scope']=='bounded_pair_delivery_diagnostic_not_motion_authority'
                assert boundary['outputs']==0 and not boundary['stopped']
            result=client.call_async(Trigger.Request())
            deadline=time.monotonic()+3.
            while not result.done() and time.monotonic()<deadline:
                executor.spin_once(timeout_sec=.02)
            assert result.done() and result.result().success
            if gated:
                clock=peer.create_publisher(Clock,'/clock',10)
                deadline=time.monotonic()+3.
                while not clock.get_subscription_count() and time.monotonic()<deadline:
                    executor.spin_once(timeout_sec=.01)
                assert clock.get_subscription_count()==1
                clock.publish(Clock())
                while 'CLOCK_CALLBACK_ENTERED' not in stdout_path.read_text() and time.monotonic()<deadline:
                    time.sleep(.005)
                assert 'CLOCK_CALLBACK_ENTERED' in stdout_path.read_text()
            process.send_signal(signal.SIGINT)
            if gated:
                # This is a lifecycle discriminator, not a robot timing input.
                time.sleep(.1)
                if process.poll() is None:
                    process.stdin.write(b'release\n');process.stdin.flush()
            process.wait(timeout=5.)
        stdout,stderr=stdout_path.read_text(),stderr_path.read_text()
        report=dict(scope='actual_ROS_adapter_RPC_SIGINT_not_engine_acceptance',
            attempt=attempt,command=command,pid=process.pid,returncode=process.returncode,
            stdout=stdout,stderr=stderr,engine_started=False,stop_ack=result.result().success)
        (tmp_path/'result.json').write_text(json.dumps(report,indent=2))
        assert process.returncode==0,stderr
        assert 'NORMAL_CONTACT_EXIT' in stdout
        assert 'Traceback' not in stderr
        if gated:
            assert 'CLOCK_CALLBACK_RETURNED_VALID_CONTEXT' in stdout, \
                'SIGINT interrupted or invalidated an outstanding real callback'
    finally:
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            if gated and process.stdin is not None and not process.stdin.closed:
                try:
                    process.stdin.write(b'release\n');process.stdin.flush()
                except BrokenPipeError:pass
            process.wait(timeout=5.)
        if process is not None and process.stdin is not None:
            process.stdin.close()
        executor.shutdown(timeout_sec=2.);peer.destroy_node();context.try_shutdown()
