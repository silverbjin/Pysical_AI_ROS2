#!/usr/bin/env python3
"""Own one actual engine; exercise the bounded tracking action and cancel path.

The explicit red-fixture detector is NOT a YOLO or grasp success. This smoke
probe does not certify tracking accuracy; section 13.4 geometric trials do that.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_prefix

from action_msgs.msg import GoalStatusArray
from controller_manager_msgs.srv import ListControllers
from integrated_robot_interfaces.msg import TrackedTarget
import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import SetBool

from probe_sensors_13_4 import stop_owned_group


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('gazebo', 'mujoco'), required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = dict(status='RUNNING', engine=args.engine, run_id=str(uuid.uuid4()),
                  started_at=time.time(), checks={}, errors=[], cleanup=[])
    path = output/'result.json'

    def save():
        path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')

    save()
    os.environ['GZ_PARTITION'] = 'ch13_tracking_'+result['run_id']
    os.environ['RCUTILS_COLORIZED_OUTPUT'] = '0'
    processes, logs = [], []
    node, initialized = None, False
    history, targets, actions, joints = [], [], [], []
    startup, latest = {}, {}
    try:
        rclpy.init()
        initialized = True
        node = rclpy.create_node('tracking_engine_probe', parameter_overrides=[
            Parameter('use_sim_time', value=True)])

        def launch(name, command):
            log = (output/(name+'.log')).open('w', encoding='utf-8')
            logs.append(log)
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            processes.append((name, process))
            return process

        def pump(duration):
            deadline = time.monotonic()+duration
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.01)

        def until(predicate, timeout=20.):
            deadline = time.monotonic()+timeout
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.01)
                if any(p.poll() is not None for _, p in processes):
                    raise RuntimeError('owned engine/runtime process exited unexpectedly')
                if predicate():
                    return
            raise TimeoutError('tracking engine probe deadline exceeded')

        def tracking(message):
            value = json.loads(message.data)
            latest.clear()
            latest.update(value)
            history.append(dict(wall=time.monotonic(), **value))

        def target(message):
            targets.append(dict(wall=time.monotonic(), valid=message.valid, status=message.status,
                                stamp=message.header.stamp.sec+message.header.stamp.nanosec/1e9,
                                ros_now=node.get_clock().now().nanoseconds/1e9,
                                processed_at=message.processed_at.sec+message.processed_at.nanosec/1e9,
                                position=[message.position.x, message.position.y, message.position.z]))

        def status(message):
            for item in message.status_list:
                actions.append(dict(wall=time.monotonic(), uuid=bytes(item.goal_info.goal_id.uuid).hex(),
                                    status=item.status))

        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = [
            node.create_subscription(String, '/architecture/startup',
                lambda m: startup.update(json.loads(m.data)), qos),
            node.create_subscription(String, '/architecture/visual_tracking', tracking, 10),
            node.create_subscription(TrackedTarget, '/vision/tracked_target', target, 20),
            node.create_subscription(GoalStatusArray,
                '/arm_trajectory_controller/follow_joint_trajectory/_action/status', status, qos),
            node.create_subscription(JointState, '/joint_states',
                lambda m: joints.append(dict(wall=time.monotonic(), names=list(m.name),
                                            positions=list(m.position))), 10)]
        engine = launch('engine', ['ros2', 'launch', 'integrated_robot_description',
                                   args.engine+'.launch.py', 'vision_enabled:=true'])
        controller = node.create_client(ListControllers, '/controller_manager/list_controllers')
        until(controller.service_is_ready, 60.)
        controllers = {}
        deadline = time.monotonic()+40.
        required = ('joint_state_broadcaster', 'leg_position_controller',
                    'arm_trajectory_controller', 'gripper_position_controller')
        while time.monotonic() < deadline:
            future = controller.call_async(ListControllers.Request())
            until(future.done, 5.)
            controllers = {v.name: v.state for v in future.result().controller}
            if all(controllers.get(v) == 'active' for v in required):
                break
            pump(.2)
        if not all(controllers.get(v) == 'active' for v in required):
            raise RuntimeError('four controllers not active')
        result['controllers'] = controllers
        for executable in ('locomotion_node', 'manipulation_node', 'state_manager'):
            # Own installed executable, not a ros2 run wrapper that may not forward SIGINT.
            launch(executable, [str(Path(get_package_prefix('integrated_robot_runtime'))/
                                   'lib/integrated_robot_runtime'/executable),
                               '--ros-args', '-p', 'use_sim_time:=true'])
        launch('detector', [str(Path(get_package_prefix('integrated_robot_vision'))/
                               'lib/integrated_robot_vision/object_detector'),
                           '--ros-args', '-p', 'use_sim_time:=true', '-p', 'backend:=color_fixture'])
        launch('fusion', [str(Path(get_package_prefix('integrated_robot_vision'))/
                             'lib/integrated_robot_vision/vision_processor'),
                         '--ros-args', '-p', 'use_sim_time:=true'])
        until(lambda: startup.get('status') in ('READY', 'FAILED'), 30.)
        if startup.get('status') != 'READY':
            raise RuntimeError('measured lifecycle startup failed: '+str(startup))
        until(lambda: any(v['valid'] for v in targets), 20.)
        pump(2.5)  # allow measured stand trajectory to settle
        result['checks']['default_off_zero_tracking_goals'] = bool(history) and all(
            v['goal_count'] == 0 and not v['enabled'] for v in history)
        toggle = node.create_client(SetBool, '/manipulation_node/set_visual_tracking')
        until(toggle.service_is_ready, 5.)
        # One explicit enable, after a fresh observation, not a timed guess and
        # not an automatic retry/re-enable of a failed tracking session.
        until(lambda: bool(targets) and targets[-1]['valid'] and
              0 <= node.get_clock().now().nanoseconds/1e9-targets[-1]['stamp'] <= .20, 10.)
        baseline_action_ids = {v['uuid'] for v in actions}
        future = toggle.call_async(SetBool.Request(data=True))
        until(future.done, 5.)
        result['enable'] = dict(success=future.result().success, message=future.result().message)
        if not future.result().success:
            raise RuntimeError('tracking enable refused: '+future.result().message)
        until(lambda: latest.get('goal_count', 0) > 0 and latest.get('outstanding'), 5.)
        before_disable = latest['goal_count']
        result['disable_requested_wall'] = time.monotonic()
        future = toggle.call_async(SetBool.Request(data=False))
        until(future.done, 5.)
        result['disable'] = dict(success=future.result().success, message=future.result().message)
        until(lambda: not latest.get('outstanding', True) and not latest.get('enabled', True), 5.)
        pump(.6)
        result['checks'].update(
            actual_valid_targets=sum(v['valid'] for v in targets) >= 5,
            dispatched_local_tracking=before_disable > 0,
            disable_acknowledged=result['disable']['success'],
            terminal_action_ack=any(v['status'] in (4, 5, 6) and v['uuid'] not in baseline_action_ids
                                    for v in actions),
            no_successor_after_disable=latest.get('goal_count') == before_disable,
            reservation_released=not latest.get('reserved', True),
            no_ownership_fault=not latest.get('fault', 'missing'))
        if not all(result['checks'].values()) or len(result['checks']) != 8:
            raise RuntimeError('one or more required tracking ownership checks failed')
        result['status'] = 'PASS'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['errors'].append(repr(exc))
    finally:
        # Request own cancellation while the executor and physical controller still run.
        if node is not None:
            try:
                client = node.create_client(SetBool, '/manipulation_node/set_visual_tracking')
                if client.wait_for_service(timeout_sec=.5):
                    future = client.call_async(SetBool.Request(data=False))
                    rclpy.spin_until_future_complete(node, future, timeout_sec=1.)
                    end = time.monotonic()+.7
                    while time.monotonic() < end:
                        rclpy.spin_once(node, timeout_sec=.02)
            except Exception as exc:
                result['errors'].append('pre-shutdown cancel: '+repr(exc))
                result['status'] = 'FAIL'
        for name, process in reversed(processes):
            if name == 'engine' and args.engine == 'gazebo':
                try:
                    response = subprocess.run(['gz', 'service', '-s', '/server_control', '--reqtype',
                        'gz.msgs.ServerControl', '--reptype', 'gz.msgs.Boolean', '--timeout', '2000',
                        '--req', 'stop: true'], capture_output=True, text=True, timeout=5.)
                    result['server_stop'] = dict(returncode=response.returncode, stdout=response.stdout)
                    time.sleep(.5)
                except Exception as exc:
                    result['errors'].append(repr(exc))
            cleanup = stop_owned_group(process)
            result['cleanup'].append(dict(name=name, pid=process.pid, returncode=process.poll(), **cleanup))
            if cleanup['residual_live_pids'] or cleanup['forced_cleanup']:
                result['status'] = 'FAIL'
        for log in logs:
            log.close()
        for name, _ in processes:
            content = (output/(name+'.log')).read_text(encoding='utf-8')
            if 'Traceback' in content or 'exception was never retrieved' in content:
                result['errors'].append(name+' raised an exception; see raw log')
                result['status'] = 'FAIL'
        if node is not None:
            node.destroy_node()
        if initialized:
            rclpy.try_shutdown()
        result.update(finished_at=time.time(), startup=startup, tracking=history,
                      targets=targets, actions=actions, joint_samples=joints)
        save()
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'errors')}, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
