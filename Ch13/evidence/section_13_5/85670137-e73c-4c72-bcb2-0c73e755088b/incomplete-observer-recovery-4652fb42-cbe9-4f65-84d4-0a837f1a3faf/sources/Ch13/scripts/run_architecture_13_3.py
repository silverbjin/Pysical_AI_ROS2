#!/usr/bin/env python3
"""Own and stop only the engine/runtime process groups started by this run."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import rclpy
from controller_manager_msgs.srv import ListControllers


def stop(process):
    from probe_sensors_13_4 import stop_owned_group
    return stop_owned_group(process, grace_s=15.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=['gazebo', 'mujoco', 'none'], required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / 'result.json'
    result_path.write_text(json.dumps({'status': 'RUNNING', 'engine': args.engine}) + '\n',
                           encoding='utf-8')
    os.environ['GZ_PARTITION'] = f'ch13_3_{os.getpid()}'
    os.environ['RCUTILS_COLORIZED_OUTPUT'] = '0'
    processes = []
    logs = []
    engine = None
    cleanup = []
    gazebo_stop = None
    rclpy.init()
    node = rclpy.create_node('architecture_engine_waiter')
    try:
        def launch(package, filename, logname):
            log = (output / logname).open('w', encoding='utf-8')
            logs.append(log)
            process = subprocess.Popen(
                ['ros2', 'launch', package, filename], stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
            processes.append(process)
            return process

        if args.engine != 'none':
            engine = launch('integrated_robot_description', f'{args.engine}.launch.py', 'engine.log')
            client = node.create_client(ListControllers, '/controller_manager/list_controllers')
            deadline = time.monotonic() + 60
            ready = False
            while time.monotonic() < deadline and engine.poll() is None:
                if not client.wait_for_service(timeout_sec=1):
                    continue
                future = client.call_async(ListControllers.Request())
                rclpy.spin_until_future_complete(node, future, timeout_sec=2)
                if future.done() and future.result() is not None:
                    states = {item.name: item.state for item in future.result().controller}
                    required = ['joint_state_broadcaster', 'leg_position_controller',
                                'arm_trajectory_controller', 'gripper_position_controller']
                    if all(states.get(name) == 'active' for name in required):
                        ready = True
                        break
            if not ready:
                raise RuntimeError('engine controllers did not activate; inspect engine.log')
        launch('integrated_robot_runtime', 'architecture.launch.py', 'runtime.log')
        with (output / 'probe.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('verify_architecture_13_3.py')),
                 '--output', str(output / 'result.json')]
                + (['--expect-startup-failure'] if args.engine == 'none' else []),
                stdout=log, stderr=subprocess.STDOUT, timeout=120)
        if result.returncode:
            raise RuntimeError('runtime integration failed; inspect probe.log and result.json')
    except Exception as exc:
        result = json.loads(result_path.read_text(encoding='utf-8'))
        result.update(status='FAIL', engine=args.engine, runner_error=str(exc))
        result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    finally:
        for process in reversed(processes):
            if process is engine and args.engine == 'gazebo':
                from run_vision_13_4 import quiesce_gazebo, owned_gazebo_members, wait_owned_members_exit
                gazebo_stop = dict(confirmed=False)
                try:
                    members = owned_gazebo_members(process)
                    if not members:
                        raise RuntimeError('owned Gazebo member missing before shutdown')
                    gazebo_stop['pause'] = quiesce_gazebo('section_13_2')
                    command = ['gz', 'service', '-s', '/server_control', '--reqtype',
                        'gz.msgs.ServerControl', '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '2000', '--req', 'stop: true']
                    response = subprocess.run(command, capture_output=True, text=True, timeout=5.)
                    gazebo_stop.update(command=command, returncode=response.returncode,
                        stdout=response.stdout, stderr=response.stderr,
                        native_exited=wait_owned_members_exit(process, members, timeout=8.))
                    gazebo_stop['confirmed'] = (gazebo_stop['pause']['confirmed']
                        and response.returncode == 0 and 'data: true' in response.stdout
                        and gazebo_stop['native_exited'])
                except Exception as exc:
                    gazebo_stop['error'] = repr(exc)
            report = stop(process)
            cleanup.append(dict(pid=process.pid, role='engine' if process is engine else 'runtime',
                                returncode=process.poll(), **report))
        for log in logs:
            log.close()
        node.destroy_node()
        rclpy.shutdown()
    result = json.loads(result_path.read_text(encoding='utf-8'))
    runtime_path = output/'runtime.log'
    runtime_log = runtime_path.read_text(encoding='utf-8') if runtime_path.is_file() else ''
    clean = ('Traceback' not in runtime_log and 'exception was never retrieved' not in runtime_log
             and runtime_log.count('process has finished cleanly') == 5)
    engine_log = (output/'engine.log').read_text(encoding='utf-8') if engine else ''
    engine_clean = (bool(cleanup) and (args.engine == 'none' or engine is not None)
                    and all(not item['forced_cleanup'] and not item['residual_live_pids']
                        and item['returncode'] == 0 for item in cleanup)
                    and not any(marker in engine_log for marker in
                        ('escalating to', 'process has died', 'failed to terminate'))
                    and (args.engine != 'gazebo' or bool(gazebo_stop and gazebo_stop.get('confirmed'))))
    result.update(engine=args.engine, runtime_shutdown='PASS' if clean else 'FAIL',
                  engine_shutdown='PASS' if engine_clean else 'FAIL', cleanup=cleanup)
    if gazebo_stop is not None:
        result['gazebo_stop'] = gazebo_stop
    if not clean or not engine_clean:
        result['status'] = 'FAIL'
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if result['status'] != 'PASS':
        raise RuntimeError('architecture or normal shutdown failed; inspect saved result/logs')


if __name__ == '__main__':
    main()
