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
    if process.poll() is None:
        # Signal launch first; it forwards SIGINT to children itself.
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
    # Ruby/gz can outlive an exited launch parent. This group was created by us
    # with start_new_session=True, so never infer a group from unrelated PIDs.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


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
        raise
    finally:
        for process in reversed(processes):
            stop(process)
        for log in logs:
            log.close()
        node.destroy_node()
        rclpy.shutdown()
    result = json.loads(result_path.read_text(encoding='utf-8'))
    runtime_log = (output / 'runtime.log').read_text(encoding='utf-8')
    clean = ('Traceback' not in runtime_log and 'exception was never retrieved' not in runtime_log
             and runtime_log.count('process has finished cleanly') == 5)
    result.update(engine=args.engine, runtime_shutdown='PASS' if clean else 'FAIL')
    if not clean:
        result['status'] = 'FAIL'
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if not clean:
        raise RuntimeError('runtime did not shut down cleanly; inspect runtime.log')


if __name__ == '__main__':
    main()
