#!/usr/bin/env python3
"""Serial native vision trials with fresh, fail-closed evidence and owned cleanup."""
import argparse
from copy import copy
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import shutil
import statistics
import subprocess
from threading import Event
import time
import xml.etree.ElementTree as ET

from verify_vision_13_4 import EvidenceRun, rms_error, geometry_summary, tf_contract_single_owners, tracking_summary, source_snapshot, file_digest
from integrated_robot_vision.trace import trace_options


COMMON = {'one_clock', 'one_odometry', 'single_tf_owners', 'sensor_contract', 'controller_backend_loaded',
          'measured_startup', 'engine_alive', 'clean_shutdown', 'native_snapshot'}


def recognition_summary(detections, tracks, expected_class=None):
    detected = [v for v in detections if any(expected_class is None or b['class_id'] == expected_class
                                             for b in v['boxes'])]
    valid = [v for v in tracks if v['valid'] and
             (expected_class is None or v['class_id'] == expected_class)]
    return dict(frames=len(detections), detected_frames=len(detected), valid_3d=len(valid),
                expected_class=expected_class, coverage=len(detected)/len(detections) if detections else 0.)


def wait_for_stage(predicate, step, timeout, *, stage, stages, snapshot=lambda: {}):
    started = time.monotonic()
    record = dict(stage=stage, started_monotonic=started, status='RUNNING')
    stages.append(record)
    try:
        while not predicate():
            if time.monotonic()-started >= timeout:
                record['status'] = 'TIMEOUT'
                raise TimeoutError('native vision verification deadline exceeded: '+stage)
            step()
        record['status'] = 'PASS'
    except BaseException:
        if record['status'] == 'RUNNING':
            record['status'] = 'ERROR'
        raise
    finally:
        record.update(finished_monotonic=time.monotonic(), last_inputs=snapshot())


def offset_fixture(engine, share, output, y):
    """Copy a physical fixture; never replace camera images or target messages."""
    if not math.isfinite(y) or abs(y) > .05:
        raise ValueError('local physical fixture offset must be within .05m')
    share, output = Path(share).resolve(), Path(output).resolve()
    if engine == 'mujoco':
        tree = ET.parse(share/'mujoco/vision_fixture.xml')
        tree.find('include').set('file', str(share/'mujoco/robot_system.xml'))
        tree.find('.//geom[@name="vision_fixture"]').set('pos', f'1 {y} .72')
        path = output/'offset_fixture.xml'
    elif engine == 'gazebo':
        tree = ET.parse(share/'worlds/vision_fixture.sdf')
        tree.find('.//model[@name="vision_fixture"]/pose').text = f'1 {y} .72 0 0 0'
        path = output/'offset_fixture.sdf'
    else:
        raise ValueError('unknown physical engine')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return path


def tracking_baseline(samples, since):
    """Require measured, distinct captures before the first control enable."""
    unique = {}
    for sample in samples:
        if sample['wall'] >= since:
            unique.setdefault(sample['capture_ns'], sample)
    selected = list(unique.values())
    errors = [sample['pixel_error'] for sample in selected]
    if (len(selected) < 3 or any(key <= 0 for key in unique)
            or not all(math.isfinite(error) and error >= 0 for error in errors)
            or statistics.median(errors) <= 1.):
        return None
    return dict(capture_ns=list(unique), pixel_errors=errors,
                measurement_walls=[sample['wall'] for sample in selected])


def clean_shutdown(cleanup, returncode, log):
    return (bool(cleanup) and returncode == 0 and all(
        not v['forced_cleanup'] and not v['residual_live_pids'] for v in cleanup)
        and not any(marker in log for marker in (
            'process has died', 'failed to terminate', 'escalating to', 'Traceback',
            'exception was never retrieved', 'Arm shutdown cancellation unconfirmed')))


def wait_owned_members_exit(process, members, *, timeout=8.):
    """Wait for parent reaping, not just absence from a non-zombie live list.

    Launch's pidfd child watcher must consume each exit status before the next
    launch SIGINT can forward another signal. Popen.send_signal polls/reaps an
    already exited child; racing that with the watcher produces exit code255.
    PID start ticks protect this read-only barrier against PID reuse.
    """
    if not math.isfinite(timeout) or not 0 < timeout <= 10.:
        raise ValueError('bounded native stop grace required')
    pending = {}
    for pid in members:
        try:
            fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) != process.pid:
                raise ValueError('refuse to wait on an unrelated process group member')
            pending[pid] = fields[19]
        except (FileNotFoundError, ProcessLookupError):
            continue
    deadline = time.monotonic()+timeout
    while pending:
        if process.pid in pending:
            # We are this Popen's parent, so only we may consume its status.
            # Other members must be reaped by their actual launch parent.
            process.poll()
        for pid, started in tuple(pending.items()):
            try:
                fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
                if fields[19] != started:
                    del pending[pid]  # original PID was reaped and recycled
            except (FileNotFoundError, ProcessLookupError):
                del pending[pid]
        if not pending:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(.05)
    return True


def stop_owned_runtime_nodes(process):
    """Close command ingress and join workers while the physical server lives.

    Only known console executables inside this launch's own process group are
    signaled. Engine, ROS bridges and robot_state_publisher remain alive here.
    """
    from probe_sensors_13_4 import live_group_pids
    names = {'locomotion_node', 'manipulation_node', 'mission_commander',
             'state_manager', 'vision_processor', 'object_detector',
             'native_pose_adapter', 'native_camera_info_adapter'}
    packages = {'integrated_robot_runtime', 'integrated_robot_vision'}
    record = dict(started_ns=time.monotonic_ns(), nodes=[], confirmed=False,
                  completion_boundary='owned children reaped by parent')
    for pid in live_group_pids(process.pid):
        try:
            argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
            for argument in argv[:2]:
                executable = Path(os.fsdecode(argument))
                if (executable.name in names and len(executable.parts) >= 3
                        and executable.parts[-2] in packages and executable.parts[-3] == 'lib'):
                    if os.getpgid(pid) != process.pid:
                        raise RuntimeError('runtime owner changed before shutdown')
                    record['nodes'].append(dict(pid=pid, executable=str(executable)))
                    os.kill(pid, signal.SIGINT)
                    break
        except ProcessLookupError:
            continue
    record['confirmed'] = bool(record['nodes']) and wait_owned_members_exit(
        process, [item['pid'] for item in record['nodes']], timeout=8.)
    record['finished_ns'] = time.monotonic_ns()
    return record


def quiesce_gazebo(world):
    """Observe a paused world before asking rendering/physics to tear down.

    Called only after the tracking/action drain. ACK is not state evidence.
    No retries, signals or timeout relaxation; a failed handshake stays FAIL.
    """
    record = dict(confirmed=False, started_ns=time.monotonic_ns(), commands=[])
    try:
        command = ['gz', 'service', '-s', f'/world/{world}/control', '--reqtype',
                   'gz.msgs.WorldControl', '--reptype', 'gz.msgs.Boolean',
                   '--timeout', '2000', '--req', 'pause: true']
        record['commands'].append(command)
        response = subprocess.run(command, capture_output=True, text=True, timeout=5.)
        record['pause'] = dict(returncode=response.returncode, stdout=response.stdout,
                               stderr=response.stderr)
        if response.returncode != 0 or 'data: true' not in response.stdout:
            return record
        command = ['gz', 'topic', '-e', '-t', f'/world/{world}/stats', '-n', '1',
                   '--json-output']
        record['commands'].append(command)
        response = subprocess.run(command, capture_output=True, text=True, timeout=5.)
        record['stats'] = dict(returncode=response.returncode, stdout=response.stdout,
                               stderr=response.stderr)
        if response.returncode == 0:
            record['confirmed'] = json.loads(response.stdout).get('paused') is True
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        record['error'] = repr(exc)
    finally:
        record['finished_ns'] = time.monotonic_ns()
    return record


def is_gazebo_command(command_line):
    args = command_line.split(b'\0')
    if args[0].startswith(b'gz sim '):
        return True  # Ruby $0/setproctitle replaces argv with one padded string.
    return (len(args) >= 3 and Path(os.fsdecode(args[0])).name.startswith('ruby')
            and Path(os.fsdecode(args[1])).name == 'gz' and args[2] == b'sim')


def snapshot_owned_stacks(process, members, output):
    """Read-only bounded debugger attach; never change ptrace policy or use sudo."""
    members = list(members)
    for pid in members:
        try:
            if os.getpgid(pid) != process.pid:
                raise ValueError('refuse stack capture of unrelated process')
        except ProcessLookupError:
            continue
    records = []
    for pid in members:
        try:
            if os.getpgid(pid) != process.pid:
                raise ValueError('owned process changed group before debugger attach')
        except ProcessLookupError:
            continue
        path = Path(output)/f'shutdown-stack-{pid}.txt'
        record = dict(pid=pid, pgid=process.pid, path=path.name)
        if shutil.which('gdb') is None:
            content = 'gdb unavailable; no package installation attempted\n'
            record['status'] = 'UNAVAILABLE'
        else:
            command = ['gdb', '--batch', '--nx', '-iex', 'set auto-load off', '-p', str(pid),
                       '-ex', 'set pagination off', '-ex', 'thread apply all bt', '-ex', 'detach']
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=12.)
                content = result.stdout+result.stderr
                record.update(returncode=result.returncode, status=(
                    'CAPTURED' if 'Thread ' in content and '#' in content else 'UNAVAILABLE'))
            except subprocess.TimeoutExpired as exc:
                content = 'bounded gdb timeout\n'+str(exc)
                record['status'] = 'TIMEOUT'
        path.write_text(content, encoding='utf-8')
        records.append(record)
    return records


def owned_gazebo_members(process):
    from probe_sensors_13_4 import live_group_pids
    found = []
    for pid in live_group_pids(process.pid):
        try:
            command_line = (Path('/proc')/str(pid)/'cmdline').read_bytes()
            wrapper = (command_line.startswith(b'/bin/sh\0-c\0ruby ')
                       and b'/gz sim ' in command_line)
            if is_gazebo_command(command_line) or wrapper:
                found.append(pid)
        except (OSError, ValueError):
            continue
    return found


def camera_launch_module():
    from ament_index_python.packages import get_package_share_directory
    path = Path(get_package_share_directory('integrated_robot_description'))/'launch/mujoco.launch.py'
    spec = importlib.util.spec_from_file_location('_ch13_installed_camera_launch', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mapped_owned_library(process, expected_library):
    """Actual library bytes in an explicitly owned launch process group."""
    from probe_sensors_13_4 import live_group_pids
    expected = Path(expected_library).resolve(strict=True)
    for pid in live_group_pids(process.pid):
        try:
            if os.getpgid(pid) != process.pid:
                continue
            for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines():
                fields = line.split(maxsplit=5)
                if len(fields) == 6 and fields[-1] == str(expected):
                    return dict(pid=pid,pgid=process.pid,library_path=str(expected),
                                library_sha256=file_digest(expected))
        except (ProcessLookupError,FileNotFoundError):
            continue
    raise RuntimeError('expected controller library not mapped in owned engine: '+str(expected))


def mapped_camera_library(pid, owned_pgid, expected_library):
    """Read only an owned group's mappings; no attach, signals or policy changes."""
    if os.getpgid(pid) != owned_pgid:
        raise ValueError('refuse library audit of unrelated process')
    expected = Path(expected_library).resolve(strict=True)
    expected_core = (expected.parent/'libsnapshot_mailbox.so').resolve(strict=True)
    if not expected_core.is_relative_to(expected.parent):
        raise RuntimeError('mailbox library resolves outside selected camera package')
    mapped = {expected.name: set(), expected_core.name: set()}
    for line in (Path('/proc')/str(pid)/'maps').read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and any(name in fields[5] for name in mapped):
            path = Path(fields[5])
            if not path.is_absolute() or not path.is_file():
                raise RuntimeError('mapped camera library missing or deleted')
            resolved = path.resolve()
            if resolved.name in mapped:
                mapped[resolved.name].add(resolved)
    if mapped[expected.name] != {expected} or mapped[expected_core.name] != {expected_core}:
        raise RuntimeError('native mapped camera library does not match selected probe')
    if os.getpgid(pid) != owned_pgid:
        raise ValueError('owned process changed group during library audit')
    return dict(library_path=str(expected), library_sha256=file_digest(expected),
                mailbox_library_path=str(expected_core), mailbox_library_sha256=file_digest(expected_core))


def audit_camera_backend(process, expected_prefix: Path) -> dict:
    from ament_index_python.packages import get_package_prefix
    from probe_sensors_13_4 import live_group_pids
    if process.poll() is not None or os.getpgid(process.pid) != process.pid:
        raise RuntimeError('native launch group is not live and independently owned')
    audit = camera_launch_module().probe_snapshot_plugin(Path(expected_prefix))
    expected_native = (Path(get_package_prefix('mujoco_ros2_control'))/
                       'lib/mujoco_ros2_control/ros2_control_node').resolve(strict=True)
    candidates = []
    for pid in live_group_pids(process.pid):
        try:
            if (Path('/proc')/str(pid)/'exe').resolve(strict=True) == expected_native:
                candidates.append(pid)
        except OSError:
            continue
    if len(candidates) != 1:
        raise RuntimeError('exactly one owned native MuJoCo control process is required')
    loaded = mapped_camera_library(candidates[0], process.pid, audit['library_path'])
    if loaded['library_sha256'] != audit['library_sha256']:
        raise RuntimeError('native camera binary changed after probe')
    log = Path(process.ch13_system_log).read_text(encoding='utf-8')
    if 'integrated_robot_camera/SnapshotCameraPlugin initialized' not in log:
        raise RuntimeError('native camera initialization class ID was not observed')
    renderer_lines = [line.split('Snapshot renderer EGL:', 1)[1].strip()
                      for line in log.splitlines() if 'Snapshot renderer EGL:' in line]
    if not renderer_lines:
        raise RuntimeError('actual snapshot EGL renderer initialization was not observed')
    from verify_all_13_4 import audit_installed_paths
    installed = audit_installed_paths(Path(expected_prefix).resolve().parent,
                                      Path(__file__).resolve().parents[2])
    if loaded['mailbox_library_sha256'] != installed['integrated_robot_camera']['mailbox_library_sha256']:
        raise RuntimeError('native mailbox binary differs from installed audit')
    return dict(audit, **loaded, native_pid=candidates[0], installed_packages=installed,
                egl_renderer=renderer_lines,
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


LEGACY_AUTO_CAMERA_TOPICS = tuple(
    f'/{camera}/{stream}' for camera in ('overview', 'eye_in_hand')
    for stream in ('color', 'depth', 'camera_info'))


def native_trace_origin_verified(records, proof):
    """Bind trace metadata to the live audited native process; never signal it."""
    if (not isinstance(proof, dict) or not proof.get('egl_renderer')
            or not proof.get('library_sha256') or not proof.get('mailbox_library_sha256')
            or type(proof.get('native_pid')) is not int or proof['native_pid'] <= 0
            or not proof.get('boot_id')):
        return False
    try:
        cameras = [row['record'] for row in records if row['record']['stage'] == 'camera']
        return bool(cameras) and all(value['pid'] == proof['native_pid'] and
            value['boot_id'] == proof['boot_id'] and value['clock_id'] == 'linux/CLOCK_MONOTONIC'
            for value in cameras)
    except (KeyError, TypeError):
        return False


def camera_publishers_unique(owners):
    return all(len(owners.get(topic, [])) == 1 for topic in (
        '/camera/color/image_raw', '/camera/aligned_depth_to_color/image_raw',
        '/native/camera_info', '/camera/color/camera_info')) and not any(
            owners.get(topic, []) for topic in LEGACY_AUTO_CAMERA_TOPICS)


def required_checks(scenario, *, engine=None, camera_backend='upstream'):
    extra = {'camera_backend_loaded', 'single_camera_owners'} if engine == 'mujoco' and camera_backend == 'snapshot' else set()
    return _scenario_checks(scenario) | extra


def _scenario_checks(scenario):
    if scenario in ('static', 'delay'):
        return COMMON | {'thirty_observations', 'geometry_rms'} | (
            {'actual_camera_motion', 'delay_150ms'} if scenario == 'delay' else set())
    if scenario == 'yolo':
        return COMMON | {'actual_inference_frames', 'recognition', 'valid_3d_detections'}
    if scenario == 'tracking':
        return COMMON | {'five_second_tracking', 'pixel_error_reduction', 'joint_limits',
                         'velocity_limits', 'command_rate'}
    if scenario == 'safety':
        return COMMON | {'actual_tracking_goal', 'fault_injected', 'input_loss_stop', 'cancel_confirmed'}
    raise ValueError('unknown trial scenario')


def build_launch_command(args, delay):
    trace = trace_options(getattr(args, 'trace_enabled', False), getattr(args, 'trace_run_id', ''))
    rate = float(getattr(args, 'inference_rate_hz', 10.))
    if not math.isfinite(rate) or not 0 < rate <= 15:
        raise ValueError('inference rate must be finite and in (0,15]')
    backend = getattr(args, 'vision_camera_backend', 'upstream')
    if backend not in ('upstream', 'snapshot'):
        raise ValueError('vision camera backend must be upstream or snapshot')
    command = ['ros2', 'launch', 'integrated_robot_runtime', 'vision_system.launch.py',
        'engine:='+args.engine, 'detector_backend:='+args.detector_backend,
        'processing_delay_s:='+str(delay), 'tracking_enabled:=false', 'max_rate_hz:='+str(rate),
        'allow_camera_motion_test:='+str(args.scenario == 'delay').lower()]
    if args.weights_path:
        command.append('weights_path:='+args.weights_path)
    if trace['trace_enabled']:
        command += ['trace_enabled:=true', 'trace_run_id:='+trace['trace_run_id']]
    if args.engine == 'mujoco':
        command.append('mujoco_headless:='+str(getattr(args, 'mujoco_headless', True)).lower())
        command.append('vision_camera_backend:='+backend)
    return command


def run_trial(args, *, launch_command=None):
    """launch_command is a process-boundary test seam, never exposed as a CLI option."""
    backend = getattr(args, 'vision_camera_backend', 'upstream')
    required = required_checks(args.scenario, engine=args.engine, camera_backend=backend)
    run = EvidenceRun(args.output_dir, required)
    args = copy(args)
    args.trace_run_id = run.run_id if getattr(args, 'trace_enabled', False) else ''
    process = log = node = None
    content = ''
    initialized, checks, cleanup = False, {}, []
    stopping = Event()
    previous_signal = None
    tracking_started, initial_errors, command_start = None, [], 0
    with run:
        try:
            run.result.update(engine=args.engine, vision_camera_backend=backend)
            if args.detector_backend == 'yolo':
                weights = Path(args.weights_path)
                if not weights.is_absolute() or not weights.is_file():
                    raise FileNotFoundError('explicit existing absolute YOLO weights required')
            if args.scenario in ('static', 'delay', 'tracking', 'safety') and args.detector_backend != 'color_fixture':
                raise ValueError('geometric fixture trials require explicit color_fixture, not YOLO fallback')
            if args.scenario == 'yolo' and args.detector_backend != 'yolo':
                raise ValueError('YOLO trial cannot use a fixture detector')
            snapshot = source_snapshot(Path(__file__).resolve().parents[2])
            (run.root/'source_snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
            run.artifact(run.root/'source_snapshot.json')
            run.result['source_head'] = snapshot['head']
            import numpy as np
            import rclpy
            from rclpy.signals import SignalHandlerOptions
            from std_srvs.srv import SetBool
            from vision_observer_13_4 import VisionObserver
            from probe_sensors_13_4 import stop_owned_group

            rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
            initialized = True
            previous_signal = signal.signal(signal.SIGINT, lambda *_: stopping.set())
            trace = trace_options(getattr(args, 'trace_enabled', False), args.trace_run_id)
            node = VisionObserver(run.root, **trace)
            os.environ['GZ_PARTITION'] = 'ch13_vision_'+run.run_id
            os.environ['RCUTILS_COLORIZED_OUTPUT'] = '0'
            delay = .15 if args.scenario == 'delay' else 0.
            if args.processing_delay_s is not None:
                delay = args.processing_delay_s
            run.result.update(engine=args.engine, detector_backend=args.detector_backend,
                              scenario=args.scenario, processing_delay_s=delay, processes=[],
                              trace_enabled=trace['trace_enabled'], trace_run_id=args.trace_run_id)
            command = launch_command or build_launch_command(args, delay)
            run.result['inference_rate_hz'] = float(getattr(args, 'inference_rate_hz', 10.))
            fixture_y = 0.
            if args.scenario == 'yolo' and getattr(args, 'semantic_fixture', 'red') == 'cup':
                from ament_index_python.packages import get_package_share_directory
                from semantic_fixture_13_4 import make_cup_fixture
                path = make_cup_fixture(args.engine,
                    get_package_share_directory('integrated_robot_description'), run.root)
                command.append(('world' if args.engine == 'gazebo' else 'model_path')+':='+str(path))
                run.artifact(path)
                run.result['semantic_fixture'] = dict(kind='authored_geometry_cup', expected_class='41',
                    note='Static hollow mug/handle and coffee on table; not a photo billboard or grasp test')
            if args.scenario in ('tracking', 'safety'):
                from ament_index_python.packages import get_package_share_directory
                fixture_y = .02
                path = offset_fixture(args.engine,
                    get_package_share_directory('integrated_robot_description'), run.root, fixture_y)
                command.append(('world' if args.engine == 'gazebo' else 'model_path')+':='+str(path))
                run.artifact(path)
                run.result['physical_fixture'] = dict(center=[1., fixture_y, .72], front_x=.98)
            log = (run.root/'system.log').open('w', encoding='utf-8')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            process.ch13_system_log = run.root/'system.log'
            run.result['processes'].append(dict(pid=process.pid, pgid=process.pid, command=command,
                                                start_new_session=True))
            run.save()
            last_clock = 0

            def step():
                nonlocal last_clock
                if stopping.is_set():
                    raise InterruptedError('operator interrupted verification')
                if process.poll() is not None:
                    raise RuntimeError('owned engine/launch process died: '+str(process.returncode))
                rclpy.spin_once(node, timeout_sec=.01)
                now = node.get_clock().now().nanoseconds
                if now < last_clock:
                    raise RuntimeError('native clock rolled backward during a measured trial')
                last_clock = now
                if args.detector_backend == 'color_fixture':
                    node.process_samples(fixture_y=fixture_y)
                if node.startup.get('status') == 'FAILED':
                    raise RuntimeError('measured startup failed: '+str(node.startup))
                if (args.scenario == 'delay' and node.collecting and node.tracking
                        and not node.tracking.get('enabled', False)):
                    raise RuntimeError('camera-motion benchmark stopped on safety gate: '+
                                       node.tracking.get('reason', 'unknown'))

            run.result['stages'] = []

            def until(predicate, timeout, stage):
                wait_for_stage(predicate, step, timeout, stage=stage, stages=run.result['stages'],
                    snapshot=lambda: dict(tracking=dict(node.tracking), counts=dict(node.counts),
                                          command_count=len(node.commands)))

            def pump(duration):
                deadline = time.monotonic()+duration
                while time.monotonic() < deadline:
                    step()

            def toggle(path, enabled):
                client = node.create_client(SetBool, path)
                try:
                    until(client.service_is_ready, 5., path+':service_ready')
                    future = client.call_async(SetBool.Request(data=enabled))
                    until(future.done, 5., path+':reply')
                    reply = future.result()
                    if not reply.success:
                        raise RuntimeError('explicit mode request refused: '+reply.message)
                    return reply.message
                finally:
                    node.destroy_client(client)

            until(lambda: node.startup.get('status') == 'READY' and node.standing(), args.timeout, 'startup')
            checks['measured_startup'] = True
            from ament_index_python.packages import get_package_prefix
            controller_prefix = Path(get_package_prefix('integrated_robot_controller')).resolve()
            controller_library = (controller_prefix/'lib/libch13_joint_trajectory_controller.so').resolve(strict=True)
            if not controller_library.is_relative_to(controller_prefix):
                raise RuntimeError('controller library resolves outside selected package')
            run.result['controller_backend_audit'] = dict(
                class_id='integrated_robot_controller/JointTrajectoryController',
                **mapped_owned_library(process,controller_library))
            checks['controller_backend_loaded'] = True
            if args.engine == 'mujoco' and backend == 'snapshot':
                from ament_index_python.packages import get_package_prefix
                audit = audit_camera_backend(process, Path(get_package_prefix('integrated_robot_camera')))
                path = run.root/'camera_backend.json'
                path.write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')
                run.artifact(path)
                run.result['camera_backend_audit'] = audit
                checks['camera_backend_loaded'] = True
                run.save()
            if args.scenario == 'delay':
                run.result['motion_enable'] = toggle('/manipulation_node/set_camera_motion_test', True)
                until(lambda: node.tracking.get('enabled') and node.tracking.get('mode') == 'camera_motion_test',
                      5., 'camera_motion_ack')
            node.collecting = True
            started = time.monotonic()
            if args.scenario in ('static', 'delay'):
                minimum = 6. if args.scenario == 'delay' else 3.
                until(lambda: len({v['capture_ns'] for v in node.samples}) >= 30
                      and time.monotonic()-started >= minimum, args.timeout, 'thirty_unique_observations')
                errors = [v['error'] for v in node.samples]
                measured = geometry_summary(node.samples, .05 if args.scenario == 'delay' else .03)
                run.result['geometry'] = dict(measured,
                    metric='capture RGB bbox ray intersect declared front surface x=.98, not object COM',
                    elapsed_wall_s=time.monotonic()-started)
                checks.update(thirty_observations=measured['unique_captures'] >= 30,
                              geometry_rms=measured['rms_m'] is not None and
                              measured['rms_m'] <= measured['rms_limit_m'] and measured['unique_timestamps'])
                if args.scenario == 'delay':
                    q1 = [v[2][0] for v in node.joints if v[1] >= started]
                    run.result['motion'] = dict(measured_q1_peak_to_peak_rad=max(q1)-min(q1),
                        nominal_amplitude_rad=.03, nominal_period_sim_s=2.,
                        measured_trace='joints.npz; this is camera motion, NOT PPO walking')
                    checks['actual_camera_motion'] = max(q1)-min(q1) >= .04
                    checks['delay_150ms'] = delay == .15
            elif args.scenario == 'yolo':
                pump(args.duration)
                expected = run.result.get('semantic_fixture', {}).get('expected_class')
                measured = recognition_summary(node.detections, node.tracks, expected)
                run.result['recognition'] = dict(measured, note='Actual native camera and YOLO; no fallback')
                checks.update(actual_inference_frames=measured['frames'] >= 10,
                              recognition=measured['detected_frames'] > 0,
                              valid_3d_detections=measured['valid_3d'] >= 5)
                node.save_latest_frame()  # retain actual sensors even if every inference expires
                for key in reversed(node.boxes):
                    # Save the actual image aligned to an actual inference result,
                    # including an honest empty annotation when recognition failed.
                    image = next((v[0] for v in node.cache.rgb.values()
                        if v[0].header.stamp.sec*1_000_000_000+v[0].header.stamp.nanosec == key), None)
                    if image is None:
                        continue
                    bundle = node.cache.match(image.header.stamp, 'camera_optical_frame', 0)
                    if bundle is not None:
                        boxes = node.boxes[key]
                        node.save_frame(bundle, boxes[0] if boxes else None)
                        break
            elif args.scenario in ('tracking', 'safety'):
                until(lambda: tracking_baseline(node.samples, started) is not None,
                      args.timeout, 'tracking_baseline')
                baseline = tracking_baseline(node.samples, started)
                baseline.update(finished_monotonic=time.monotonic(), command_count=len(node.commands))
                run.result['tracking_baseline'] = baseline
                initial = baseline['pixel_errors']
                initial_errors = initial
                until(lambda: bool(node.tracks) and node.tracks[-1]['valid']
                      and 0 <= node.get_clock().now().nanoseconds-node.tracks[-1]['capture_ns'] <= .2e9,
                      args.timeout, 'fresh_target')
                command_start = len(node.commands)
                request_at = time.monotonic()
                run.result['tracking_enable'] = toggle('/manipulation_node/set_visual_tracking', True)
                until(lambda: any(v.get('event') == 'enable_ack' and v['wall'] >= request_at
                                  for v in node.states), 2., 'tracking_ack')
                acknowledgement = next(v for v in reversed(node.states)
                                       if v.get('event') == 'enable_ack' and v['wall'] >= request_at)
                session = acknowledgement['session_generation']
                run.result['tracking_session'] = dict(requested_monotonic=request_at,
                                                     acknowledgement=acknowledgement)
                enabled_at = time.monotonic()
                tracking_started = enabled_at
                def started_session():
                    if not node.tracking.get('enabled'):
                        raise RuntimeError('tracking stopped before fault/trial: '+str(node.tracking))
                    return any(v.get('session_generation') == session and
                               v['dispatched_monotonic'] >= request_at
                               for v in node.commands[command_start:])
                until(started_session, 3., 'first_tracking_command')
                if args.scenario == 'tracking':
                    while time.monotonic()-enabled_at < 5.2:
                        step()
                        if not node.tracking.get('enabled', False):
                            raise RuntimeError('tracking latched OFF before five seconds: '+str(node.tracking))
                    final = [v['pixel_error'] for v in node.samples if v['wall'] >= time.monotonic()-1.]
                    metrics = tracking_summary(node.commands[command_start:], initial, final,
                        elapsed=time.monotonic()-enabled_at,
                        measured_positions=[v[2] for v in node.joints if v[1] >= enabled_at],
                        measured_velocities=[v for v, j in zip(node.joint_velocities, node.joints)
                                             if j[1] >= enabled_at])
                    run.result['tracking_metrics'] = metrics
                    checks.update(metrics['checks'])
                else:
                    # Record healthy ownership BEFORE intentional removal of a source.
                    before = {t: [v.node_name for v in node.get_publishers_info_by_topic(t)]
                              for t in ('/tf', '/tf_static')}
                    checks['single_tf_owners'] = tf_contract_single_owners(before, node.tf_parents, node.model_parents)
                    fault = getattr(args, 'fault', 'images')
                    fault_record = dict(kind=fault, requested_monotonic=time.monotonic())
                    if fault == 'images':
                        fault_record['reply'] = toggle('/object_detector/set_input_enabled', False)
                        fault_record['scope'] = 'detector consumer ingress; native camera remains publishing'
                    elif fault == 'tf':
                        from probe_sensors_13_4 import live_group_pids
                        pids = []
                        for pid in live_group_pids(process.pid):
                            try:
                                argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
                                if Path(os.fsdecode(argv[0])).name == 'robot_state_publisher':
                                    pids.append(pid)
                            except OSError:
                                continue
                        if len(pids) != 1 or os.getpgid(pids[0]) != process.pid:
                            raise RuntimeError('cannot identify exactly one owned robot_state_publisher')
                        os.kill(pids[0], signal.SIGINT)
                        fault_record['owned_pid'] = pids[0]
                    elif fault == 'joints':
                        from controller_manager_msgs.srv import SwitchController
                        client = node.create_client(SwitchController, '/controller_manager/switch_controller')
                        try:
                            until(client.service_is_ready, 3., 'joint_switch_ready')
                            request = SwitchController.Request(deactivate_controllers=['joint_state_broadcaster'],
                                strictness=2, activate_asap=True)
                            request.timeout.sec = 2
                            future = client.call_async(request)
                            until(future.done, 3., 'joint_switch_reply')
                            if not future.result().ok:
                                raise RuntimeError('joint broadcaster deactivation refused')
                            fault_record['scope'] = 'joint_state_broadcaster only; consequently joint TF also becomes stale'
                        finally:
                            node.destroy_client(client)
                    else:
                        raise ValueError('unknown input loss')
                    fault_record['effective_monotonic'] = time.monotonic()
                    run.result['fault'] = fault_record
                    pump(1.2)
                    cutoff = fault_record['effective_monotonic']+.3+.2
                    checks.update(actual_tracking_goal=len(node.commands) > command_start, fault_injected=True,
                        input_loss_stop=not node.tracking.get('enabled', True) and
                            not any(v['dispatched_monotonic'] > cutoff for v in node.commands),
                        cancel_confirmed=not node.tracking.get('outstanding', True))
                    run.result['fault']['goal_stop_deadline_monotonic'] = cutoff
                    run.result['fault']['final_tracking'] = node.tracking
            owners = {topic: [v.node_name for v in node.get_publishers_info_by_topic(topic)]
                      for topic in ('/clock', '/odom', '/camera/color/image_raw',
                                    '/camera/aligned_depth_to_color/image_raw', '/native/camera_info',
                                    '/camera/color/camera_info', '/tf', '/tf_static')
                      + LEGACY_AUTO_CAMERA_TOPICS}
            run.result['owners'] = owners
            if args.engine == 'mujoco' and backend == 'snapshot':
                checks['single_camera_owners'] = camera_publishers_unique(owners)
            images = node.latest_images
            checks.update(one_clock=len(owners['/clock']) == 1, one_odometry=len(owners['/odom']) == 1,
                sensor_contract=all(k in images and images[k].header.frame_id == 'camera_optical_frame'
                                    and images[k].width == 320 and images[k].height == 240
                                    and node.counts[k] >= 30 for k in ('rgb', 'depth', 'info')),
                engine_alive=process.poll() is None and node.get_clock().now().nanoseconds > 0)
            checks.setdefault('single_tf_owners', tf_contract_single_owners(owners, node.tf_parents, node.model_parents))
            checks['native_snapshot'] = node.saved_frame
            run.result['startup'] = node.startup
            run.result['tf_ownership_method'] = 'graph+model-parent-contract inference; Jazzy does not expose packet GID'
            run.result['versions'] = {key: importlib.metadata.version(key)
                for key in ('numpy', 'mujoco', 'ultralytics', 'torch', 'opencv-python')}
            git = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
            run.result['source_head'] = git.stdout.strip() if git.returncode == 0 else 'UNAVAILABLE'
        except Exception as exc:
            run.fail(repr(exc))
        finally:
            if initialized:
                import rclpy
                from std_srvs.srv import SetBool
                from probe_sensors_13_4 import stop_owned_group
                if node is not None:
                    try:
                        client = node.create_client(SetBool, '/manipulation_node/set_visual_tracking')
                        if client.wait_for_service(timeout_sec=.3):
                            future = client.call_async(SetBool.Request(data=False))
                            rclpy.spin_until_future_complete(node, future, timeout_sec=1.)
                            deadline = time.monotonic()+1.
                            while time.monotonic() < deadline:
                                rclpy.spin_once(node, timeout_sec=.02)
                                if node.tracking and not node.tracking.get('outstanding', True):
                                    break
                            if node.tracking.get('outstanding'):
                                run.fail('own trajectory terminal cancellation not confirmed')
                        if args.scenario == 'tracking' and 'tracking_metrics' not in run.result:
                            selected = [i for i, v in enumerate(node.joints)
                                        if tracking_started is not None and v[1] >= tracking_started]
                            metrics = tracking_summary(node.commands[command_start:], initial_errors, [],
                                elapsed=time.monotonic()-tracking_started if tracking_started else 0.,
                                measured_positions=[node.joints[i][2] for i in selected],
                                measured_velocities=[node.joint_velocities[i] for i in selected])
                            run.result['tracking_metrics'] = metrics
                            checks.update(metrics['checks'])
                        node.save()
                        if args.scenario in ('static', 'delay'):
                            partial = geometry_summary(node.samples, .05 if args.scenario == 'delay' else .03)
                            run.result.setdefault('geometry', partial)
                            checks.setdefault('thirty_observations', partial['unique_captures'] >= 30)
                            checks.setdefault('geometry_rms', partial['rms_m'] is not None and
                                partial['rms_m'] <= partial['rms_limit_m'] and partial['unique_timestamps'])
                    except Exception as exc:
                        run.fail('pre-shutdown/evidence failure: '+repr(exc))
            if process is not None:
                if launch_command is None:
                    try:
                        run.result['runtime_stop'] = stop_owned_runtime_nodes(process)
                        if not run.result['runtime_stop']['confirmed']:
                            run.fail('owned runtime shutdown unconfirmed before engine stop')
                    except Exception as exc:
                        run.fail('runtime stop failure: '+repr(exc))
                if args.engine == 'gazebo' and launch_command is None:
                    try:
                        native_members = owned_gazebo_members(process)
                        if not native_members:
                            raise RuntimeError('owned Gazebo native/launcher members could not be identified')
                        run.result['gazebo_quiescence'] = quiesce_gazebo('section_13_4')
                        if not run.result['gazebo_quiescence']['confirmed']:
                            run.fail('Gazebo world pause was not observed before shutdown')
                        response = subprocess.run(['gz', 'service', '-s', '/server_control', '--reqtype',
                            'gz.msgs.ServerControl', '--reptype', 'gz.msgs.Boolean', '--timeout', '2000',
                            '--req', 'stop: true'], capture_output=True, text=True, timeout=5.)
                        run.result['gazebo_stop'] = dict(returncode=response.returncode, stdout=response.stdout)
                        # ServerControl ACK means accepted, not that rendering threads
                        # have joined. Wait for our actual native child before signaling
                        # the remaining ROS launch group; do not guess a .5s delay.
                        run.result['gazebo_native_stop'] = dict(pids=native_members,
                            exited=wait_owned_members_exit(process, native_members, timeout=8.))
                        if not run.result['gazebo_native_stop']['exited']:
                            run.result['shutdown_stacks'] = snapshot_owned_stacks(process, native_members, run.root)
                    except Exception as exc:
                        run.fail('native stop failure: '+repr(exc))
                try:
                    cleanup.append(dict(pid=process.pid, **stop_owned_group(process)))
                    run.result['launch_returncode'] = process.poll()
                except Exception as exc:
                    run.fail('owned cleanup failed: '+repr(exc))
            if log is not None:
                log.close()
                content = (run.root/'system.log').read_text(encoding='utf-8')
                if ('Traceback' in content or 'exception was never retrieved' in content
                        or 'Arm shutdown cancellation unconfirmed' in content):
                    run.fail('native/runtime exception; inspect system.log')
            checks['clean_shutdown'] = clean_shutdown(cleanup, process.poll() if process else None, content)
            if launch_command is None:
                checks['clean_shutdown'] = checks['clean_shutdown'] and (
                    run.result.get('runtime_stop', {}).get('confirmed') is True)
            if args.engine == 'gazebo' and launch_command is None and process is not None:
                stop = run.result.get('gazebo_stop', {})
                checks['clean_shutdown'] = checks['clean_shutdown'] and (
                    stop.get('returncode') == 0 and 'data: true' in stop.get('stdout', '')
                    and run.result.get('gazebo_quiescence', {}).get('confirmed') is True)
            if node is not None:
                if getattr(args, 'trace_enabled', False):
                    try:
                        # Bounded drain of diagnostic callbacks after our engine
                        # has exited; never wait for trace to control the robot.
                        for _ in range(128):
                            rclpy.spin_once(node, timeout_sec=0.)
                        native = args.engine == 'mujoco' and backend == 'snapshot'
                        summary = node.save_trace(require_native=native)
                        proof = run.result.get('camera_backend_audit', {})
                        if native and not native_trace_origin_verified(node.trace_collector.records, proof):
                            summary.update(analysis_status='UNVERIFIED', native_boundary='UNVERIFIED',
                                           segments={})
                            summary['errors'].append(
                                'actual EGL/owned PID/boot/library evidence missing or mismatched')
                            (run.root/'trace_summary.json').write_text(
                                json.dumps(summary, indent=2)+'\n', encoding='utf-8')
                        run.result['trace_analysis'] = summary
                    except Exception as exc:
                        # Diagnostic success/failure is separate from native
                        # physics, terminal action and clean shutdown verdicts.
                        run.result['trace_analysis'] = dict(analysis_status='UNVERIFIED',
                            errors=[repr(exc)])
                node.destroy_node()
            if initialized:
                rclpy.try_shutdown()
            if previous_signal is not None:
                signal.signal(signal.SIGINT, previous_signal)
            run.result['cleanup'] = cleanup
            names = ['observations.json', 'joints.npz', 'system.log']
            if getattr(args, 'trace_enabled', False):
                names += ['trace.jsonl', 'trace_summary.json']
            names += [v['path'] for v in run.result.get('shutdown_stacks', [])]
            if node is not None and node.saved_frame:
                names += ['rgb.png', 'depth.npy', 'annotated.png', 'camera.json']
            for name in names:
                path = run.root/name
                if path.exists():
                    run.artifact(path)
        try:
            run.finish(checks)
        except RuntimeError:
            pass  # FAIL is persisted and returned as nonzero by main.
    return run.result


def run_geometry_trials(args, overall):
    phases = {}
    for scenario in ('static', 'delay'):
        trial = copy(args)
        trial.scenario, trial.output_dir = scenario, str(overall.root/scenario)
        phases[scenario] = run_trial(trial)
        overall.artifact(Path(trial.output_dir)/'result.json')
        overall.result['phases'] = {key: value['status'] for key, value in phases.items()}
        overall.save()
        cleanup = phases[scenario].get('cleanup')
        if not cleanup or any(item.get('residual_live_pids') != [] for item in cleanup):
            raise RuntimeError('Owned cleanup unconfirmed; refusing another geometry engine')
    return phases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('gazebo', 'mujoco'), required=True)
    parser.add_argument('--detector-backend', choices=('yolo', 'color_fixture'), default='yolo')
    parser.add_argument('--weights-path', default='')
    parser.add_argument('--scenario', choices=('geometry', 'static', 'delay', 'yolo', 'tracking', 'safety'))
    parser.add_argument('--fault', choices=('images', 'tf', 'joints'), default='images')
    viewer = parser.add_mutually_exclusive_group()
    viewer.add_argument('--mujoco-headless', dest='mujoco_headless', action='store_true', default=True)
    viewer.add_argument('--mujoco-viewer', dest='mujoco_headless', action='store_false')
    parser.add_argument('--semantic-fixture', choices=('red', 'cup'), default='cup')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--timeout', type=float, default=60.)
    parser.add_argument('--duration', type=float, default=20.)
    parser.add_argument('--processing-delay-s', type=float)
    parser.add_argument('--inference-rate-hz', type=float, default=10.)
    parser.add_argument('--vision-camera-backend', choices=('upstream', 'snapshot'), default='upstream')
    parser.add_argument('--trace-enabled', action='store_true')
    args = parser.parse_args()
    args.scenario = args.scenario or ('geometry' if args.detector_backend == 'color_fixture' else 'yolo')
    if args.scenario == 'geometry':
        with EvidenceRun(args.output_dir, {'static', 'delay'}) as overall:
            phases = run_geometry_trials(args, overall)
            try:
                overall.finish({key: value['status'] == 'PASS' for key, value in phases.items()})
            except RuntimeError:
                pass
        result = overall.result
    else:
        result = run_trial(args)
    print(json.dumps({key: result.get(key) for key in ('run_id', 'status', 'checks', 'errors')}, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
