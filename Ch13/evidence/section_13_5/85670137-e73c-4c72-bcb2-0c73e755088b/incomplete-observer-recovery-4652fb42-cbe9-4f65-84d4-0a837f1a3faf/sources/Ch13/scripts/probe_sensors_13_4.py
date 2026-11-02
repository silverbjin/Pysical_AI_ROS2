#!/usr/bin/env python3
"""Real-engine smoke test; artifacts are observations, never synthesized images."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

import cv2
from cv_bridge import CvBridge
from controller_manager_msgs.srv import ListControllers
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, CameraInfo
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener


def live_group_pids(pgid):
    result = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                result.append(int(path.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return sorted(result)


def stop_owned_group(process, grace_s=2.):
    """Caller must have created this process with start_new_session=True."""
    pgid = process.pid
    if pgid == os.getpgrp():
        raise ValueError('refuse to signal the caller process group')
    report = dict(forced_cleanup=False, residual_live_pids=[])
    if process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            report['forced_cleanup'] = True
    # The group must be checked even if the parent returned successfully.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not live_group_pids(pgid):
            break
        report['forced_cleanup'] = True
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + grace_s
        while time.monotonic() < deadline and live_group_pids(pgid):
            time.sleep(.02)
    if process.poll() is None:
        process.wait(timeout=5)
    report['residual_live_pids'] = live_group_pids(pgid)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('gazebo', 'mujoco'), required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--timeout', type=float, default=60.)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = dict(status='RUNNING', engine=args.engine, run_id=str(uuid.uuid4()),
                  started_at=time.time(), counts={}, errors=[])
    result_path = output / 'result.json'

    def save():
        result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    save()
    process, log, node = None, None, None
    initialized = False
    os.environ['GZ_PARTITION'] = 'ch13_4_' + result['run_id']
    os.environ['RCUTILS_COLORIZED_OUTPUT'] = '0'
    try:
        rclpy.init()
        initialized = True
        node = rclpy.create_node('sensor_smoke_13_4', parameter_overrides=[
            rclpy.parameter.Parameter('use_sim_time', value=True)])
        buffer = Buffer(node=node)
        listener = TransformListener(buffer, node)
        received, stamps = {}, {}
        counts = {key: 0 for key in ('rgb', 'depth', 'info', 'odom')}
        subscriptions = []

        def collect(key, message):
            received[key] = message
            counts[key] += 1
            stamps.setdefault(key, []).append(message.header.stamp.sec +
                                              message.header.stamp.nanosec / 1e9)

        for key, topic, kind in (
                ('rgb', '/camera/color/image_raw', Image),
                ('depth', '/camera/aligned_depth_to_color/image_raw', Image),
                ('info', '/camera/color/camera_info', CameraInfo),
                ('odom', '/odom', Odometry)):
            subscriptions.append(node.create_subscription(
                kind, topic, lambda msg, key=key: collect(key, msg), qos_profile_sensor_data))
        log = (output / 'engine.log').open('w', encoding='utf-8')
        process = subprocess.Popen(['ros2', 'launch', 'integrated_robot_description',
                                    args.engine + '.launch.py', 'vision_enabled:=true'],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + args.timeout
        pose = None
        controller_client = node.create_client(ListControllers, '/controller_manager/list_controllers')
        controller_future = None
        states = {}
        required_controllers = {'joint_state_broadcaster', 'leg_position_controller',
                                'arm_trajectory_controller', 'gripper_position_controller'}
        while time.monotonic() < deadline and process.poll() is None:
            rclpy.spin_once(node, timeout_sec=.05)
            if controller_future is not None and controller_future.done():
                response = controller_future.result()
                if response is not None:
                    states = {item.name: item.state for item in response.controller}
                controller_future = None
            if controller_future is None and controller_client.service_is_ready():
                controller_future = controller_client.call_async(ListControllers.Request())
            if min(counts.values()) >= 10:
                try:
                    pose = buffer.lookup_transform('odom', 'camera_optical_frame',
                                                   Time.from_msg(received['rgb'].header.stamp))
                    if all(states.get(k) == 'active' for k in required_controllers):
                        break
                except Exception:
                    pass
        result['counts'] = counts
        result['stamps'] = stamps
        result['controllers'] = states
        if (min(counts.values()) < 10 or pose is None or not
                all(states.get(k) == 'active' for k in required_controllers)):
            raise RuntimeError('insufficient real RGB-D/TF or controllers not active')
        rgb, depth, info = (received[key] for key in ('rgb', 'depth', 'info'))
        bridge = CvBridge()
        bgr = bridge.imgmsg_to_cv2(rgb, 'bgr8')
        depth_array = bridge.imgmsg_to_cv2(depth, 'passthrough')
        if not cv2.imwrite(str(output / 'rgb.png'), bgr):
            raise RuntimeError('RGB artifact write failed')
        np.save(output / 'depth.npy', depth_array, allow_pickle=False)
        result['camera'] = dict(width=info.width, height=info.height, k=list(info.k),
                                r=list(info.r), p=list(info.p), d=list(info.d),
                                frame=info.header.frame_id, depth_encoding=depth.encoding)
        result['optical_in_odom'] = dict(
            translation=[pose.transform.translation.x, pose.transform.translation.y,
                         pose.transform.translation.z],
            quaternion_xyzw=[pose.transform.rotation.x, pose.transform.rotation.y,
                             pose.transform.rotation.z, pose.transform.rotation.w],
            stamp=pose.header.stamp.sec + pose.header.stamp.nanosec/1e9)
        result['owners'] = {topic: [v.node_name for v in node.get_publishers_info_by_topic(topic)]
                            for topic in ('/clock', '/odom', '/tf', '/tf_static',
                                          '/camera/color/image_raw')}
        checks = dict(
            dimensions=(rgb.width == depth.width == info.width == 320 and
                        rgb.height == depth.height == info.height == 240),
            optical_headers=(rgb.header.frame_id == depth.header.frame_id ==
                             info.header.frame_id == 'camera_optical_frame'),
            advancing=all(max(stamps[k]) > min(stamps[k]) > 0 for k in stamps),
            one_clock=len(result['owners']['/clock']) == 1,
            one_odometry=len(result['owners']['/odom']) == 1,
            actual_depth=bool(np.isfinite(depth_array).any()),
            rectification=bool(np.array_equal(np.array(info.r).reshape(3, 3), np.eye(3))),
        )
        result['checks'] = checks
        if not all(checks.values()):
            raise RuntimeError('sensor contract failed')
        result['status'] = 'PASS'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['errors'].append(repr(exc))
    finally:
        if process is not None:
            result['launch_pid'] = process.pid
            if args.engine == 'gazebo' and process.poll() is None:
                try:
                    response = subprocess.run([
                        'gz', 'service', '-s', '/server_control', '--reqtype',
                        'gz.msgs.ServerControl', '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '2000', '--req', 'stop: true'],
                        capture_output=True, text=True, timeout=5)
                    result['server_stop'] = dict(returncode=response.returncode,
                                                stdout=response.stdout, stderr=response.stderr)
                    time.sleep(.5)
                except Exception as exc:
                    result['server_stop'] = dict(error=repr(exc))
            result.update(stop_owned_group(process))
            if result['residual_live_pids']:
                result['status'] = 'FAIL'
                result['errors'].append('owned native processes remain after cleanup')
            result['launch_returncode'] = process.poll()
        if node is not None:
            node.destroy_node()
        if initialized:
            rclpy.try_shutdown()
        if log is not None:
            log.close()
        result['finished_at'] = time.time()
        save()
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
