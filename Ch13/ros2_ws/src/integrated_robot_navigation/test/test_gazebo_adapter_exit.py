"""Actual adapter process/ROS service/SIGINT; no physics engine is started."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rcl_interfaces.srv import GetParameters
from integrated_robot_navigation.scene import materialize_scene


def test_ready_contact_adapter_handles_own_sigint_as_normal_exit(tmp_path):
    materialize_scene('gazebo', 'g1', tmp_path/'scene')
    context = Context()
    rclpy.init(context=context)
    peer = rclpy.create_node('adapter_exit_peer', context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(peer)
    client = peer.create_client(GetParameters, '/gazebo_contact_adapter/get_parameters')
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])+os.pathsep+env.get('PYTHONPATH', '')
    log_path = tmp_path/'adapter-process.log'
    process = None
    try:
        with log_path.open('w') as log:
            process = subprocess.Popen([sys.executable, '-c',
                'from integrated_robot_navigation.gazebo_contacts import main; main()',
                '--ros-args', '-p', 'scene_dir:='+str(tmp_path/'scene')],
                env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            assert client.wait_for_service(timeout_sec=12.), log_path.read_text()
            request = client.call_async(GetParameters.Request(names=['scene_dir']))
            executor.spin_until_future_complete(request, timeout_sec=3.)
            assert request.done() and request.result().values[0].string_value == str(tmp_path/'scene')
            assert process.poll() is None
            process.send_signal(signal.SIGINT)  # only this owned ready adapter PID
            process.wait(timeout=5.)
        assert process.returncode == 0, log_path.read_text()
        assert 'KeyboardInterrupt' not in log_path.read_text()
    finally:
        if process is not None and process.poll() is None:
            process.terminate()  # failed fixture only; never credited as a normal exit
            process.wait(timeout=5.)
        executor.shutdown(timeout_sec=2.)
        peer.destroy_node()
        context.try_shutdown()
