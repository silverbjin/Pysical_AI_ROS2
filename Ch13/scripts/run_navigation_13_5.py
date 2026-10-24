#!/usr/bin/env python3
"""Serial native G1/G2 runner. Missing measurements stay FAIL, never candidate PASS."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import signal
import subprocess
from threading import Event
import time
import traceback

import rclpy
from rclpy.signals import SignalHandlerOptions
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_srvs.srv import Trigger
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.carry_profile import CarryProfile, G1_REQUIRED, swept_footprint
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.scene import load_scene
from ament_index_python.packages import get_package_prefix, get_package_share_directory

from probe_navigation_13_5 import NavigationProbe, ProbeReceiver
from probe_sensors_13_4 import live_group_pids, stop_owned_group
from run_vision_13_4 import (clean_shutdown, mapped_owned_library, owned_gazebo_members,
                            quiesce_gazebo, wait_owned_members_exit, is_gazebo_command)
from verify_all_13_4 import audit_installed_paths
from verify_vision_13_4 import EvidenceRun, file_digest
from verify_navigation_13_5 import (FRAME_REQUIRED, assess_frames, assess_tf_ownership,
    assess_native_controls, assess_gazebo_controls, carry_terminal, normal_teardown, engine_returncodes,
    assess_g1_sensors, assess_carry_admission, operational_frames)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def stop_gazebo_observer():
    """Stop native egress before engine destruction; ACK is NOT an exit proof."""
    command = ['gz','service','-s','/navigation/stop_native_observer',
        '--reqtype','gz.msgs.Empty','--reptype','gz.msgs.Boolean','--timeout','2000','--req','']
    try:
        response = subprocess.run(command,capture_output=True,text=True,timeout=5.)
        return dict(command=command,returncode=response.returncode,stdout=response.stdout,
            stderr=response.stderr,confirmed=response.returncode == 0 and
            re.search(r'^\s*data:\s*true\s*$',response.stdout,re.MULTILINE) is not None)
    except (subprocess.TimeoutExpired,OSError) as error:
        return dict(command=command,confirmed=False,error=repr(error))


def process_identity(pid, *, proc_root=Path('/proc')):
    stat = (proc_root/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, ppid=int(stat[1]), pgid=int(stat[2]), start_ticks=int(stat[19]))


def attest_gazebo_libraries(process, members, expected, *, proc_root=Path('/proc')):
    """Bind bytes/inode/device to the same live direct native child, not a shell."""
    required = {'libnavigation_gazebo_observer.so', 'libnavigation_gazebo_observation.so',
                'libnavigation_position_system.so'}
    try:
        if len(members) != 1 or len(expected) != 3:
            raise ValueError('one native child and three libraries required')
        member = members[0]
        directory = proc_root/str(member['pid'])
        identity = process_identity(member['pid'], proc_root=proc_root)
        if (directory.stat().st_uid != os.getuid() or identity['ppid'] != process.pid
                or identity['pgid'] != process.pid or any(identity[k] != member[k] for k in identity)
                or not is_gazebo_command((directory/'cmdline').read_bytes())):
            raise ValueError('native process ownership/identity changed')
        paths = {Path(item['path']).name: Path(item['path']).resolve(strict=True) for item in expected}
        if set(paths) != required:
            raise ValueError('wrong selected libraries')
        stats = {}
        for item in expected:
            path = Path(item['path']).resolve(strict=True)
            stat = path.stat()
            stats[path] = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if file_digest(path) != item['sha256']:
                raise ValueError('selected bytes changed')
        seen = {name: set() for name in required}
        for line in (directory/'maps').read_text().splitlines():
            fields = line.split(maxsplit=5)
            if len(fields) != 6 or Path(fields[5]).name not in required:
                continue
            path = Path(fields[5]).resolve(strict=True)
            name = Path(fields[5]).name
            major, minor = (int(value,16) for value in fields[3].split(':'))
            if (path != paths[name] or int(fields[4]) != stats[path][1]
                    or os.makedev(major,minor) != stats[path][0]):
                raise ValueError('mapped path/inode/device differs')
            seen[name].add(path)
        if any(seen[name] != {paths[name]} for name in required):
            raise ValueError('missing native mappings')
        if process_identity(member['pid'], proc_root=proc_root) != identity:
            raise ValueError('native PID changed during observation')
        for path, before in stats.items():
            after = path.stat()
            if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) != before:
                raise ValueError('selected library changed during observation')
        return dict(**identity, libraries=expected, scope='live_native_mapping_not_exit_proof')
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        raise RuntimeError('Gazebo native library attestation: '+str(error)) from error


def process_metrics(pid, expected_pgid, *, proc_root=Path('/proc')):
    path = Path(proc_root)/str(pid)/'stat'
    stat = path.read_text().rsplit(')', 1)[1].split()
    if int(stat[2]) != expected_pgid:
        raise RuntimeError(f'CPU sample process-group ownership changed: pid={pid}')
    if stat[0] in ('Z', 'X', 'x'):
        raise ProcessLookupError(f'CPU sample pid={pid} exited')
    owner_before = path.stat().st_uid
    current = path.read_text().rsplit(')', 1)[1].split()
    if (current[19], current[2]) != (stat[19], stat[2]):
        raise RuntimeError(f'CPU sample identity changed: pid={pid}')
    if current[0] in ('Z', 'X', 'x'):
        raise ProcessLookupError(f'CPU sample pid={pid} exited')
    owner_after = path.stat().st_uid
    if owner_before != os.getuid() or owner_after != os.getuid():
        # Linux may change /proc/PID/stat's file owner to root during exit even
        # though the child's real/effective UID never changed. Only the same
        # confirmed dead identity is an exit race; live/foreign/reused stays fatal.
        terminal = path.read_text().rsplit(')', 1)[1].split()
        if ((terminal[19], terminal[2]) == (stat[19], stat[2])
                and terminal[0] in ('Z', 'X', 'x')):
            raise ProcessLookupError(f'CPU sample pid={pid} exited')
        raise RuntimeError(f'CPU sample ownership changed: pid={pid}, state={terminal[0]}, '
            f'start_ticks={terminal[19]}, file_uid_before={owner_before}, file_uid_after={owner_after}')
    stat = current
    return dict(pid=pid, ppid=int(stat[1]), pgid=int(stat[2]), start_ticks=int(stat[19]),
        user_ticks=int(stat[11]), system_ticks=int(stat[12]), minor_faults=int(stat[7]),
        major_faults=int(stat[9]), threads=int(stat[17]), resident_pages=int(stat[21]))


def no_existing_engines():
    found = []
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            if path.stat().st_uid != os.getuid():
                continue
            command = path.read_bytes()
            first = command.split(b'\0')[0]
            if Path(os.fsdecode(first)).name == 'ros2_control_node' or is_gazebo_command(command):
                found.append(dict(pid=int(path.parent.name), command=os.fsdecode(command).replace('\0', ' ')))
        except (OSError, ValueError):
            continue
    if found:
        raise RuntimeError('existing native engine is not owned by this invocation: '+str(found))


def runtime_git_identity(repo, source_paths):
    """Record every hashed runtime source, not the growing evidence tree."""
    paths = sorted(set(source_paths))
    if not paths or any(Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
        raise ValueError('explicit repository-relative runtime source scope required')
    return dict(
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        dirty_scope='hashed_runtime_files_only',
        dirty=subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all',
                                       '--', *('./'+p for p in paths)], cwd=repo, text=True))


def audit_description_launches(repo, share):
    """A changed source launch cannot silently execute stale installed bytes."""
    source = repo/'Ch13/ros2_ws/src/integrated_robot_description/launch'
    hashes = {}
    for engine in ('mujoco', 'gazebo'):
        original, installed = source/(engine+'.launch.py'), share/'launch'/(engine+'.launch.py')
        try:
            if (not installed.resolve(strict=True).is_relative_to(share.resolve())
                    or original.read_bytes() != installed.read_bytes()):
                raise RuntimeError('description launch source/install mismatch: '+engine)
        except OSError as error:
            raise RuntimeError('description launch missing: '+engine) from error
        hashes[str(original.relative_to(repo))] = file_digest(original)
    return hashes


def audit_runtime(repo, output):
    prefix = Path(get_package_prefix('integrated_robot_navigation')).resolve().parent
    audit = audit_installed_paths(prefix, repo)
    source = repo/'Ch13/ros2_ws/src/integrated_robot_navigation'
    installed = Path(importlib.util.find_spec('integrated_robot_navigation').origin).resolve().parent
    if not installed.is_relative_to(prefix):
        raise RuntimeError('navigation did not import selected installed prefix')
    hashes = {}
    for path in (source/'integrated_robot_navigation').glob('*.py'):
        if path.read_bytes() != (installed/path.name).read_bytes():
            raise RuntimeError('source/install mismatch: '+str(path))
        hashes[str(path.relative_to(repo))] = file_digest(path)
    share = Path(get_package_share_directory('integrated_robot_navigation'))
    for directory in ('launch', 'config'):
        for path in (source/directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                if path.read_bytes() != (share/path.relative_to(source)).read_bytes():
                    raise RuntimeError('share source/install mismatch: '+str(path))
                hashes[str(path.relative_to(repo))] = file_digest(path)
    audit['integrated_robot_navigation'] = dict(module=str(installed), source_hashes=hashes)
    description = Path(get_package_share_directory('integrated_robot_description'))
    if not description.resolve().is_relative_to(prefix):
        raise RuntimeError('description launch outside selected prefix')
    hashes.update(audit_description_launches(repo, description))
    audit['integrated_robot_description']['launch_source_verified'] = True
    upstream_gz = Path(get_package_share_directory('ros_gz_sim'))/'launch/gz_sim.launch.py'
    audit['integrated_robot_description']['upstream_gazebo_launcher'] = dict(
        path=str(upstream_gz.resolve()), sha256=file_digest(upstream_gz))
    sensors = Path(get_package_prefix('integrated_robot_navigation_sensors'))
    manifest = json.loads((sensors/'share/integrated_robot_navigation_sensors/source_manifest.json').read_text())
    for relative, expected in manifest.items():
        path = repo/'Ch13/ros2_ws/src/integrated_robot_navigation_sensors'/relative
        if file_digest(path) != expected:
            raise RuntimeError('sensor source/compiled manifest mismatch: '+str(path))
        hashes[str(path.relative_to(repo))] = expected
    sensor_probe = json.loads(subprocess.check_output(
        [str(sensors/'lib/integrated_robot_navigation_sensors/navigation_sensor_probe')], text=True))
    if sensor_probe['mujoco_header'] != sensor_probe['mujoco_library']:
        raise RuntimeError('native sensor ABI mismatch')
    observer = (sensors/'lib/integrated_robot_navigation_sensors/tf_provenance').resolve(strict=True)
    if not observer.is_relative_to(sensors):
        raise RuntimeError('TF observer outside selected package prefix')
    sensor_probe.update(tf_observer_path=str(observer), tf_observer_sha256=file_digest(observer))
    libraries = []
    for name in ('libnavigation_gazebo_observer.so', 'libnavigation_gazebo_observation.so',
                 'libnavigation_position_system.so'):
        library = (sensors/'lib'/name).resolve(strict=True)
        if not library.is_relative_to(sensors.resolve()):
            raise RuntimeError('Gazebo library outside selected sensor prefix')
        libraries.append(dict(path=str(library), sha256=file_digest(library)))
    sensor_probe['gazebo_libraries'] = libraries
    audit['integrated_robot_navigation_sensors'] = sensor_probe
    for path in (repo/'Ch13/scripts').glob('*.py'):
        hashes[str(path.relative_to(repo))] = file_digest(path)
    save(output/'source_manifest.json', dict(files=hashes, **runtime_git_identity(repo, hashes)))
    save(output/'install_manifest.json', audit)
    return prefix, sensor_probe


def stop_runtime(process):
    names = {'motion_guard', 'crawl_controller', 'carry_manager', 'nav_projection', 'crawl_startup',
             'gazebo_contact_adapter', 'native_pose_adapter', 'native_camera_info_adapter', 'tf_provenance'}
    packages = {'integrated_robot_navigation', 'integrated_robot_vision', 'integrated_robot_navigation_sensors'}
    members = []
    for pid in live_group_pids(process.pid):
        try:
            arguments = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
            for argument in arguments[:2]:
                executable = Path(os.fsdecode(argument))
                if (executable.name in names and len(executable.parts) >= 3
                        and executable.parts[-2] in packages and executable.parts[-3] == 'lib'):
                    identity = process_identity(pid)
                    if identity['pgid'] != process.pid:
                        raise RuntimeError('runtime process ownership changed')
                    members.append({**identity, 'executable': str(executable)})
                    os.kill(pid, signal.SIGINT)
                    break
        except ProcessLookupError:
            continue
    return dict(members=members, confirmed=bool(members) and wait_owned_members_exit(
        process, [row['pid'] for row in members], timeout=8.))


def run(args):
    if args.scenario != 'sensors-carry':
        raise RuntimeError('G2 execution is not enabled before the native G1 gate is implemented and passed')
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    required = G1_REQUIRED | FRAME_REQUIRED | {'contact_lift', 'native_ctrl_observed',
                                             'native_library_loaded', 'tf_observer_owned'}
    with EvidenceRun(root, required) as evidence:
        evidence.result.update(kind='native', gate='G1', engine=args.engine,
                               engine_started=False, phase='preflight_scene',
                               native_scope='in-progress: no promotion without every required measurement')
        evidence.save()
        process, probe, executor, log, metrics_log = None, None, None, None, None
        initialized = False
        checks, teardown = {}, {}
        phase_measurements = {}
        engine_members = {}
        observer_members = {}
        ownership_graph_single = False
        stopping = Event()
        previous = signal.signal(signal.SIGINT, lambda *_: stopping.set())
        try:
            repo = Path(__file__).resolve().parents[2]
            scene = load_scene(args.engine, args.scene_dir)
            model = compile_model(Path(scene['robot']['path']).read_text())
            profile = CarryProfile(**json.loads(Path(args.profile).read_text()))
            swept_footprint(model, profile, profile.limits)
            evidence.result['phase'] = 'preflight_install'
            evidence.save()
            prefix, sensor = audit_runtime(repo, root)
            no_existing_engines()
            if os.environ.get('LD_PRELOAD'):
                raise RuntimeError('unaccounted LD_PRELOAD; refusing native provenance ambiguity')
            command = ['ros2', 'launch', 'integrated_robot_navigation', 'crawl_system.launch.py',
                'engine:='+args.engine, 'navigation_scene:='+str(Path(args.scene_dir).resolve()),
                'carry_profile:='+str(Path(args.profile).resolve()), 'validation_mode:=true',
                'tf_provenance_output:='+str(root/'tf_provenance.jsonl')]
            evidence.result.update(command=command, model_sha256=model.model_sha256,
                config_sha256=profile.config_sha256, physics_sha256=profile.physics_sha256,
                scene=scene, environment={key: os.environ.get(key) for key in (
                    'ROS_DOMAIN_ID', 'MUJOCO_GL', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LP_NUM_THREADS')})
            evidence.save()
            rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
            initialized = True
            probe = NavigationProbe(root, engine=args.engine)
            executor = ProbeReceiver(probe)
            log = (root/'system.log').open('w', encoding='utf-8')
            metrics_log = (root/'process_metrics.jsonl').open('x', encoding='utf-8')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            evidence.result.update(engine_started=True, phase='measured_startup')
            evidence.result['launch_identity'] = process_identity(process.pid)
            evidence.result.update(cpu_clock_ticks_per_s=os.sysconf('SC_CLK_TCK'),
                                   boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
            evidence.save()
            last_member_scan = 0.
            last_metrics_scan = 0.

            def step():
                nonlocal last_member_scan, last_metrics_scan
                if stopping.is_set():
                    raise RuntimeError('operator interrupted native trial')
                if process.poll() is not None:
                    raise RuntimeError('owned engine/launch exited: '+str(process.returncode))
                # Only direct native/launcher children have exit status delivered
                # to this launch parent. Preserve PID start ticks before teardown.
                scan_due = time.monotonic()-last_member_scan >= .25
                members = live_group_pids(process.pid) if scan_due else ()
                if scan_due:
                    last_member_scan = time.monotonic()
                if scan_due and time.monotonic()-last_metrics_scan >= 1.:
                    last_metrics_scan = time.monotonic()
                    rows = []
                    for pid in members:
                        try:
                            row = process_metrics(pid, process.pid)
                            argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
                            row['executable'] = ' '.join(os.fsdecode(value) for value in argv[:2])
                            rows.append(row)
                        except (OSError, ValueError, IndexError):
                            continue  # raced a normal owned process exit; never sample a replacement
                    metrics_log.write(json.dumps(dict(wall_ns=time.monotonic_ns(),
                        system_ns=time.time_ns(), members=rows))+'\n')
                    metrics_log.flush()
                for pid in members:
                    try:
                        identity = process_identity(pid)
                        if identity['ppid'] != process.pid or pid in engine_members:
                            continue
                        command_line = (Path('/proc')/str(pid)/'cmdline').read_bytes()
                        executable = Path(os.fsdecode(command_line.split(b'\0')[0]))
                        if executable.name == 'tf_provenance' and pid not in observer_members:
                            actual = (Path('/proc')/str(pid)/'exe').resolve(strict=True)
                            if (str(actual) != sensor['tf_observer_path']
                                    or file_digest(actual) != sensor['tf_observer_sha256']):
                                raise RuntimeError('actual TF observer differs from installed attestation')
                            observer_members[pid] = {**identity, 'executable': str(actual),
                                                     'sha256': file_digest(actual)}
                            evidence.result['tf_observer_members'] = list(observer_members.values())
                            evidence.save()
                        native = executable.name == 'ros2_control_node' or is_gazebo_command(command_line)
                        wrapper = command_line.startswith(b'/bin/sh\0-c\0ruby ') and b'/gz sim ' in command_line
                        if native or wrapper:
                            engine_members[pid] = {**identity, 'command': os.fsdecode(command_line).replace('\0', ' ')}
                            evidence.result['engine_members'] = list(engine_members.values())
                            evidence.save()
                    except (OSError, ValueError):
                        continue
                executor.check()
                stopping.wait(.005)  # caller polling cannot busy-spin against ingress
                if not probe.ignore_faults and probe.fault():
                    raise RuntimeError('native runtime fault: '+probe.fault())

            def wait(predicate, seconds, stage):
                start = time.monotonic()
                while not predicate():
                    if time.monotonic()-start >= seconds:
                        raise TimeoutError(stage+' wall deadline; last states='+json.dumps(probe.motion))
                    step()

            def call(client, request, seconds=3.):
                wait(client.service_is_ready, seconds, client.srv_name+' discovery')
                future = client.call_async(request)
                wait(future.done, seconds, client.srv_name+' response')
                return future.result()

            wait(lambda: probe.motion.get('startup', {}).get('ready') is True, 55., 'measured startup')
            checks['carry_measured_settle'] = True
            report = json.loads(call(probe.carry_report, Trigger.Request()).message)
            save(root/'action_results.json', report)
            checks['carry_terminal_received'] = carry_terminal(report)
            if args.engine == 'gazebo':
                save(root/'native_mapping.json', attest_gazebo_libraries(
                    process, list(engine_members.values()), sensor['gazebo_libraries']))
                checks['native_library_loaded'] = True
            rejection = call(probe.mode, SetMode.Request(mode='CRAWL'))
            checks['unvalidated_crawl_rejected'] = not rejection.accepted
            started_ros, started_wall = probe.get_clock().now().nanoseconds, time.monotonic_ns()
            probe.set_stage('stand')
            evidence.result['phase'] = 'static_measurements'
            evidence.save()
            wait(lambda: probe.get_clock().now().nanoseconds-started_ros >= 10_000_000_000
                 and time.monotonic_ns()-started_wall >= 10_000_000_000, 40., 'static native measurements')
            phase_measurements['stand'] = dict(start_ros_ns=started_ros, start_wall_ns=started_wall,
                ros_duration_s=(probe.get_clock().now().nanoseconds-started_ros)/1e9,
                wall_duration_s=(time.monotonic_ns()-started_wall)/1e9)
            probe.set_stage('calibrate')
            evidence.result['phase'] = 'contact_calibration'
            evidence.save()
            calibration_ros, calibration_wall = probe.get_clock().now().nanoseconds, time.monotonic_ns()
            calibration = call(probe.calibrate, Trigger.Request())
            if not calibration.success:
                raise RuntimeError('owned contact calibration rejected: '+calibration.message)
            wait(lambda: probe.motion.get('crawl', {}).get('state') == 'CALIBRATING', 2., 'calibration start')
            wait(lambda: probe.motion.get('crawl', {}).get('state') == 'STAND'
                 and probe.motion['crawl']['stopped'], 10., 'measured calibration landing/settle')
            phase_measurements['calibration'] = dict(start_ros_ns=calibration_ros, start_wall_ns=calibration_wall,
                ros_duration_s=(probe.get_clock().now().nanoseconds-calibration_ros)/1e9,
                wall_duration_s=(time.monotonic_ns()-calibration_wall)/1e9)
            evidence.result['phase'] = 'owner_attestation'
            evidence.save()
            graph = probe.owner_graph()
            save(root/'ownership.json', dict(topics=graph, transforms=probe.transform_snapshot()))
            ownership_graph_single = all(len(rows) == 1 for rows in graph.values())
            if args.engine == 'mujoco':
                save(root/'native_mapping.json', mapped_owned_library(process, sensor['library']))
                checks['native_library_loaded'] = True
            else:
                save(root/'native_mapping_final.json', attest_gazebo_libraries(
                    process, list(engine_members.values()), sensor['gazebo_libraries']))
        except BaseException as error:
            (root/'error_traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
            evidence.result['failure_phase'] = evidence.result['phase']
            evidence.fail(type(error).__name__+': '+str(error))
        finally:
            carry_owner_report = None
            if probe:
                probe.set_stage('shutdown', ignore_faults=True)
            if process and process.poll() is None and probe and executor:
                try:
                    report = call(probe.crawl_report, Trigger.Request())
                    if not report.success:
                        raise RuntimeError('crawl report rejected')
                    save(root/'controller_report.json', json.loads(report.message))
                except Exception as error:
                    evidence.fail('controller diagnostic capture: '+repr(error))
                try:
                    report = call(probe.carry_report, Trigger.Request())
                    if not report.success:
                        raise RuntimeError('carry report rejected')
                    carry_owner_report = json.loads(report.message)
                    save(root/'carry_failure_report.json', carry_owner_report)
                except Exception as error:
                    evidence.fail('carry diagnostic capture: '+repr(error))
                try:
                    call(probe.mode, SetMode.Request(mode='STOP'))
                    wait(lambda: probe.motion.get('crawl', {}).get('stopped') is True, 3., 'shutdown measured stop')
                    call(probe.lifecycle, ChangeState.Request(transition=Transition(id=Transition.TRANSITION_DEACTIVATE)))
                    call(probe.carry_stop, Trigger.Request())
                    report = json.loads(call(probe.carry_report, Trigger.Request()).message)
                    save(root/'shutdown_action_results.json', report)
                    if report['pending_uuid'] is not None:
                        raise RuntimeError('shutdown action result remains unconfirmed')
                    if args.engine == 'mujoco':
                        response = call(probe.native_stop, Trigger.Request())
                        teardown['native_sensor_worker_joined'] = response.success
                    teardown['runtime_stop'] = stop_runtime(process)
                    teardown['runtime_exit'] = teardown['runtime_stop']['confirmed']
                except Exception as error:
                    evidence.fail('runtime stop: '+repr(error))
            if process:
                try:
                    if args.engine == 'gazebo' and process.poll() is None:
                        members = owned_gazebo_members(process)
                        teardown['native_observer_stop'] = stop_gazebo_observer()
                        if not teardown['native_observer_stop']['confirmed']:
                            evidence.fail('native observer egress stop unconfirmed')
                        teardown['gazebo_pause'] = quiesce_gazebo('section_13_5')
                        response = subprocess.run(['gz', 'service', '-s', '/server_control', '--reqtype',
                            'gz.msgs.ServerControl', '--reptype', 'gz.msgs.Boolean', '--timeout', '2000',
                            '--req', 'stop: true'], capture_output=True, text=True, timeout=5.)
                        teardown['gazebo_stop'] = dict(returncode=response.returncode, stdout=response.stdout)
                        teardown['engine_exit'] = (teardown['native_observer_stop']['confirmed']
                            and bool(members) and teardown['gazebo_pause']['confirmed'] and (
                            response.returncode == 0 and 'data: true' in response.stdout
                            and wait_owned_members_exit(process, members, timeout=8.)))
                    cleanup = stop_owned_group(process)
                    teardown.update(cleanup, launch_returncode=process.poll(), parent_reaped=process.poll() is not None)
                    if args.engine == 'mujoco':
                        teardown['engine_exit'] = process.returncode == 0 and not cleanup['forced_cleanup']
                except Exception as error:
                    evidence.fail('owned cleanup: '+repr(error))
            if log:
                log.close()
            if metrics_log:
                metrics_log.close()
            if executor:
                teardown['probe_receiver_joined'] = executor.shutdown(timeout_sec=2.)
                if not teardown['probe_receiver_joined']:
                    raise RuntimeError('probe callback not joined; ROS handles and log retained')
            if probe:
                save(root/'native_controls.json', dict(kind='native_observations_not_command_topics',
                    records=probe.native_controls, diagnostic_errors=probe.transport_errors))
                observations = dict(root_source='native_ground_truth', urdf=model.urdf,
                    frames=operational_frames(probe.frames), phases=phase_measurements)
                if args.engine == 'mujoco':
                    observations['native_body_references'] = [
                        dict(value['body_reference'], capture_ns=value['capture_ns'],
                             epoch=value['epoch'], sequence=value['sequence'])
                        for value in probe.native_controls if 'body_reference' in value]
                else:
                    # Odometry is a filtered pose-difference estimate, not the
                    # instantaneous independent physics reference for the IMU.
                    observations['odometry_body_references'] = probe.body_references
                    observations['native_body_references'] = [reference
                        for packet in probe.native_controls
                        for reference in packet.get('body_references',[])]
                save(root/'frames.json', observations)
                save(root/'all_frames.json', dict(root_source='native_ground_truth', frames=probe.frames))
                checks.update(assess_frames(observations, profile.limits))
                sensor_report = assess_g1_sensors(observations, Path(scene['world']['path']).read_text(), args.engine)
                save(root/'g1_sensor_assessment.json', sensor_report)
                checks.update(sensor_report['checks'])
                carry_report = assess_carry_admission(observations, profile.arm_q, carry_owner_report)
                save(root/'carry_hold_assessment.json', carry_report)
                checks['carry_measured_settle'] = (checks.get('carry_measured_settle') is True
                                                  and carry_report['passed'])
                if args.engine == 'mujoco':
                    checks['native_ctrl_observed'] = (checks.get('native_library_loaded') is True
                        and not probe.transport_errors and assess_native_controls(
                            [row for row in probe.native_controls if row['stage'] in ('stand', 'calibrate')],
                            model, Path(scene['world']['path']).read_text()))
                else:
                    control_report = {}
                    measured = assess_gazebo_controls(
                        [row for row in probe.native_controls if row['stage'] in ('stand','calibrate')],
                        model,Path(scene['world']['path']).read_text(),report=control_report)
                    save(root/'native_controls_assessment.json',control_report)
                    checks['native_ctrl_observed'] = (checks.get('native_library_loaded') is True
                        and not probe.transport_errors and measured)
                save(root/'probe_diagnostics.json', dict(errors=probe.errors, missing=dict(probe.missing),
                    final_states=probe.motion, all_frames=len(probe.frames), tf_python_api=probe.tf_api,
                    transport_errors=probe.transport_errors))
                probe.close_log()
            if probe:
                probe.destroy_node()
            if initialized:
                rclpy.try_shutdown()
            signal.signal(signal.SIGINT, previous)
            content = (root/'system.log').read_text() if (root/'system.log').exists() else ''
            teardown['engine_members'] = list(engine_members.values())
            teardown['engine_returncodes'] = engine_returncodes(content, list(engine_members))
            teardown['tf_observer_members'] = list(observer_members.values())
            observer_codes = engine_returncodes(content, list(observer_members))
            teardown['tf_observer_returncodes'] = observer_codes
            checks['tf_observer_owned'] = (len(observer_members) == 1 and observer_codes == [0])
            try:
                records = [json.loads(line) for line in (root/'tf_provenance.jsonl').read_text().splitlines()]
                checks['joint_tf_ownership'] = (ownership_graph_single and checks['tf_observer_owned']
                                               and assess_tf_ownership(records, model))
            except (OSError, ValueError):
                checks['joint_tf_ownership'] = False
            clean = (normal_teardown(teardown) and teardown.get('probe_receiver_joined') is True
                     and clean_shutdown([teardown], teardown.get('launch_returncode'), content))
            checks.update(normal_runtime_exit=clean and teardown.get('runtime_exit') is True,
                normal_engine_exit=clean and teardown.get('engine_exit') is True,
                parent_reaped=teardown.get('parent_reaped') is True,
                no_residual_members=teardown.get('residual_live_pids') == [])
            save(root/'teardown.json', teardown)
            for path in root.iterdir():
                if path.is_file() and path.name != 'result.json' and '.tmp' not in path.name:
                    evidence.artifact(path)
            evidence.finish(checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('mujoco', 'gazebo'), required=True)
    parser.add_argument('--scenario', choices=('sensors-carry', 'crawl-cycle', 'crawl-reverse'), required=True)
    parser.add_argument('--scene-dir', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
