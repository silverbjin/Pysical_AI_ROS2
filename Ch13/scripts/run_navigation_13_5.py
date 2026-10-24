#!/usr/bin/env python3
"""Serial native G1/G2 runner. Missing measurements stay FAIL, never candidate PASS."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import signal
import shlex
import subprocess
import sys
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


def g1_profile_arguments(node,root):
    if node is None:return []
    if node!='motion_guard':raise ValueError('only owned motion_guard diagnostic is supported')
    target=Path(root)/'motion_guard.prof'
    if target.exists():raise ValueError('profile output already exists')
    return ['launch-prefix:='+shlex.join([sys.executable,'-m','cProfile','-o',str(target)]),
            'launch-prefix-filter:=^motion_guard$']


def native_required_checks(clock_mode,contact_mode,engine,*,profile_node=None):
    if clock_mode not in ('native','relay100') or contact_mode not in ('native','allowance50um'):
        raise ValueError('unknown native experiment mode')
    if contact_mode!='native' and engine!='gazebo':
        raise ValueError('DART contact experiment requires Gazebo G1')
    required=G1_REQUIRED|FRAME_REQUIRED|{'contact_lift','native_ctrl_observed','native_library_loaded','tf_observer_owned'}
    if clock_mode=='relay100':required=required|{'control_clock_contract'}
    if contact_mode=='allowance50um':required=required|{'dart_contact_contract'}
    if profile_node is not None:
        if profile_node!='motion_guard':raise ValueError('unknown diagnostic profile target')
        required=required|{'unprofiled_acceptance'}
    return required


def read_dart_contact_probe(prefix):
    sensors=Path(get_package_prefix('integrated_robot_navigation_sensors')).resolve()
    executable=(sensors/'lib/integrated_robot_navigation_sensors/navigation_dart_contact_probe').resolve(strict=True)
    if not executable.is_relative_to(Path(prefix).resolve()):
        raise RuntimeError('native DART probe outside selected install')
    command=[str(executable)]
    report=json.loads(subprocess.check_output(command,text=True,timeout=5.))
    if type(report.get('current_m')) not in (float,int) or report['current_m']!=0.:
        raise RuntimeError('unexpected native DART default allowance')
    library=Path(report['library_path']).resolve(strict=True)
    if library.name!='libdart.so.'+report['header_version']:
        raise RuntimeError('native DART probe header/provider mismatch')
    report.update(command=command,executable_sha256=file_digest(executable),library_sha256=file_digest(library))
    return report


def assess_dart_contact_configuration(records,expected):
    report=dict(scope='native_api_configuration_not_contact_task_success',passed=False,records=len(records))
    try:
        if (not expected or type(expected.get('current_m')) not in (float,int) or expected['current_m']!=0.
                or file_digest(Path(expected['library_path']))!=expected['library_sha256']):
            raise ValueError('missing/changed preflight DART provider')
        seen=set();phases=set()
        for packet in records:
            identity=tuple(packet[k] for k in ('epoch','sequence','capture_ns'))
            if any(type(v) is not int or v<0 for v in identity) or identity in seen:
                raise ValueError('duplicate/invalid native setting capture')
            seen.add(identity);phases.add(packet['stage'])
            state=packet['dart_contact_configuration']
            if (type(state.get('schema')) is not int or state['schema']!=1 or state.get('mode')!='allowance50um'
                    or type(state.get('world_count')) is not int or state['world_count']!=1
                    or state.get('explicit_g1') is not True or state.get('header_version')!=expected['header_version']
                    or state.get('library_path')!=expected['library_path']):
                raise ValueError('unbound native DART configuration')
            for key,value in (('before_m',0.),('requested_m',.00005),('effective_m',.00005)):
                if type(state.get(key)) not in (float,int) or not math.isfinite(state[key]) or state[key]!=value:
                    raise ValueError('DART setting not actually applied or changed: '+key)
        if not {'stand','calibrate'}<=phases:raise ValueError('missing operational DART setting witnesses')
        report['passed']=True
    except (KeyError,ValueError,TypeError,OSError) as error:
        report['error']=str(error)
    return report


def control_clock_launch_arguments(mode, root):
    if mode == 'native':
        return []
    if mode != 'relay100':
        raise ValueError('unknown control_clock_mode')
    return ['control_clock_mode:=relay100', 'control_clock_output:='+str(root/'control_clock.jsonl')]


def assess_control_clock_graph(graph):
    consumers = {'motion_guard', 'crawl_controller', 'carry_manager', 'nav_projection', 'crawl_startup'}
    return (len(graph.get('source_publishers', [])) == 1
        and graph.get('relay_publishers') == ['navigation_control_clock']
        and len(graph.get('relay_subscribers', [])) == 5
        and set(graph['relay_subscribers']) == consumers
        and not consumers.intersection(graph.get('source_subscribers', []))
        and 'navigation_control_clock' in graph.get('source_subscribers', []))


def assess_control_clock_trace(rows):
    result = dict(passed=False, scope='producer_trace_not_independent_wire_proof', publications=0)
    try:
        if not rows or rows[-1]['event'] != 'closed' or any(
                row['event'] not in ('publish','armed') for row in rows[:-1]):
            raise ValueError('missing close, fault, or post-close publication')
        report = rows[-1]['report']
        if (report['mode'] != 'relay100' or report['fault'] or report['closing'] is not True
                or report.get('armed') is not True):
            raise ValueError('unhealthy final relay report')
        arms = [row for row in rows if row['event'] == 'armed']
        if len(arms) != 1:
            raise ValueError('one explicit operational arm event required')
        armed = arms[0]
        state = armed['report']
        if (state['armed'] is not True or state['fault'] or state['closing']
                or state['mode'] != 'relay100' or state['gid'] != report['gid']
                or state['last_source_capture_ns'] <= 0
                or not 0 <= armed['wall_ns']-state['last_source_receipt_ns'] <= 200000000):
            raise ValueError('arm did not bind a fresh positive original clock')
        publications = [row for row in rows if row['event'] == 'publish']
        event_walls = [row['published_wall_ns'] if row['event'] == 'publish' else row['wall_ns'] for row in rows]
        if event_walls != sorted(event_walls):
            raise ValueError('relay event chronology changed')
        previous = None
        for index, row in enumerate(publications, 1):
            stamp, wall = row['capture_ns'], row['published_wall_ns']
            if (not all(type(row[key]) is int for key in ('capture_ns','sec','nanosec',
                    'received_wall_ns','published_wall_ns','inputs','outputs'))
                    or row['sec'] < 0 or not 0 <= row['nanosec'] < 1000000000
                    or stamp != row['sec']*1000000000+row['nanosec']
                    or not 0 <= wall-row['received_wall_ns'] <= 200000000
                    or row['outputs'] != index or row['inputs'] < index
                    or not row['gid'] or row['gid'] != report['gid']):
                raise ValueError('invalid original time, receipt lease, identity, or count')
            if previous and (stamp <= previous['capture_ns']
                    or wall-previous['published_wall_ns'] < 10000000
                    or row['inputs'] <= previous['inputs']):
                raise ValueError('clock/rate/count rollback')
            previous = row
        if not previous or report['outputs'] != len(publications) or report['inputs'] < previous['inputs']:
            raise ValueError('missing or inconsistent publications')
        if rows[-1]['wall_ns'] < previous['published_wall_ns']:
            raise ValueError('close predates publication')
        result.update(passed=True, publications=len(publications), armed_wall_ns=armed['wall_ns'],
            max_receipt_age_ns=max(row['published_wall_ns']-row['received_wall_ns'] for row in publications))
    except (KeyError, TypeError, ValueError, IndexError) as error:
        result['error'] = str(error)
    return result


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


def attest_control_clock(process, pid, expected, *, proc_root=Path('/proc')):
    """Observe live owned PID and mapped library. This is not an exit proof."""
    try:
        directory = proc_root/str(pid)
        identity = process_identity(pid, proc_root=proc_root)
        actual = (directory/'exe').resolve(strict=True)
        library = Path(expected['control_clock_library']).resolve(strict=True)
        before = library.stat()
        if (directory.stat().st_uid != os.getuid() or identity['ppid'] != process.pid
                or identity['pgid'] != process.pid or str(actual) != expected['control_clock_path']
                or file_digest(actual) != expected['control_clock_sha256']
                or file_digest(library) != expected['control_clock_library_sha256']):
            raise ValueError('owned relay identity or installed bytes differ')
        found = False
        for line in (directory/'maps').read_text().splitlines():
            fields = line.split(maxsplit=5)
            if len(fields) != 6 or Path(fields[5]).name != library.name:
                continue
            major, minor = (int(part,16) for part in fields[3].split(':'))
            if (Path(fields[5]).resolve(strict=True) != library or int(fields[4]) != before.st_ino
                    or os.makedev(major,minor) != before.st_dev):
                raise ValueError('mapped relay library differs')
            found = True
        after = library.stat()
        if (not found or process_identity(pid, proc_root=proc_root) != identity
                or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) !=
                   (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)):
            raise ValueError('missing or changed relay mapping')
        return dict(**identity, executable=str(actual), sha256=expected['control_clock_sha256'],
            library=str(library), library_sha256=expected['control_clock_library_sha256'])
    except (OSError, KeyError, TypeError, ValueError, IndexError) as error:
        raise RuntimeError('control clock attestation: '+str(error)) from error


def attest_gazebo_libraries(process, members, expected, *, proc_root=Path('/proc'),dart_provider=None):
    """Bind bytes/inode/device to the same live direct native child, not a shell."""
    required = {'libnavigation_gazebo_observer.so', 'libnavigation_gazebo_observation.so',
                'libnavigation_position_system.so'}
    try:
        if len(members) != 1 or len(expected) != 3:
            raise ValueError('one native child and three libraries required')
        if dart_provider is not None:
            provider=Path(dart_provider['library_path'])
            if provider.name!='libdart.so.'+dart_provider['header_version']:
                raise ValueError('wrong DART provider/version')
            required=required|{provider.name}
            expected=[*expected,dict(path=str(provider),sha256=dart_provider['library_sha256'])]
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


def audit_python_source_bytes(source, installed, repo, prefix):
    """Bind reused Python sources to actual selected installation before launch."""
    source,installed,repo,prefix=map(Path,(source,installed,repo,prefix))
    hashes={}
    try:
        if not installed.resolve(strict=True).is_relative_to(prefix.resolve(strict=True)):
            raise RuntimeError('Python dependency outside selected installed prefix: '+str(installed))
        for path in sorted(source.rglob('*.py')):
            if '__pycache__' in path.parts:continue
            target=installed/path.relative_to(source)
            if (not target.resolve(strict=True).is_relative_to(prefix.resolve())
                    or path.read_bytes()!=target.read_bytes()):
                raise RuntimeError('Python dependency source/install mismatch: '+str(path))
            hashes[str(path.relative_to(repo))]=file_digest(path)
    except OSError as error:
        raise RuntimeError('Python dependency source/install missing: '+str(installed)) from error
    if not hashes:raise RuntimeError('Python dependency source scope is empty: '+str(source))
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
    for dependency in ('integrated_robot_runtime','integrated_robot_vision'):
        original=repo/'Ch13/ros2_ws/src'/dependency/dependency
        actual=Path(importlib.util.find_spec(dependency).origin).resolve().parent
        bound=audit_python_source_bytes(original,actual,repo,prefix)
        audit[dependency].update(module=str(actual),source_hashes=bound)
        hashes.update(bound)
    from integrated_robot_navigation.dispatch_node import event_backend_manifest
    audit['navigation_event_backend']=event_backend_manifest()
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
    clock = (sensors/'lib/integrated_robot_navigation_sensors/control_clock_relay').resolve(strict=True)
    clock_library = (sensors/'lib/libnavigation_control_clock.so').resolve(strict=True)
    if not clock.is_relative_to(sensors.resolve()) or not clock_library.is_relative_to(sensors.resolve()):
        raise RuntimeError('control clock outside selected package prefix')
    sensor_probe.update(control_clock_path=str(clock), control_clock_sha256=file_digest(clock),
                        control_clock_library=str(clock_library),
                        control_clock_library_sha256=file_digest(clock_library))
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


def wait_launch_event_exit(process,*,timeout_s=8.):
    """Observe the engine's launch exit event without injecting another signal.

    A timeout stays failed; the caller still performs explicit owned cleanup.
    """
    timed_out=False
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out=True
    return dict(confirmed=not timed_out and process.returncode==0,
                returncode=process.poll(),timed_out=timed_out,signal_sent=False)


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


def shutdown_runtime_in_order(*, measured_stop, deactivate, carry_terminal, consumers_stop,
                              native_stop=None, clock_stop=None):
    """Preserve failed safety stages, still release consumers before their clock.

    No retries, synthetic terminal results, or false normal-exit substitution.
    Engine shutdown/parent exit status remain separate caller responsibilities.
    """
    steps, errors = {}, []
    for name, operation in (('measured_stop',measured_stop), ('deactivate',deactivate),
            ('carry_terminal',carry_terminal), ('native_stop',native_stop),
            ('consumers_stop',consumers_stop), ('clock_stop',clock_stop)):
        if operation is None:
            continue
        if name == 'clock_stop' and steps.get('consumers_stop') is not True:
            steps[name] = False
            errors.append(dict(step=name,error='consumer exit unconfirmed; clock retained'))
            continue
        try:
            if operation() is not True:
                raise RuntimeError('stage result was not explicitly confirmed')
            steps[name] = True
        except Exception as error:
            steps[name] = False
            errors.append(dict(step=name,error=repr(error)))
    return dict(steps=steps, errors=errors, consumers_exited=steps.get('consumers_stop') is True,
                runtime_exit=bool(steps) and all(value is True for value in steps.values()))


def run(args):
    if args.scenario != 'sensors-carry':
        raise RuntimeError('G2 execution is not enabled before the native G1 gate is implemented and passed')
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    clock_mode = getattr(args, 'control_clock_mode', 'native')
    contact_mode=getattr(args,'dart_contact_mode','native')
    profile_node=getattr(args,'profile_node',None)
    required=native_required_checks(clock_mode,contact_mode,args.engine,profile_node=profile_node)
    clock_arguments = control_clock_launch_arguments(clock_mode, root)
    profile_arguments=g1_profile_arguments(profile_node,root)
    with EvidenceRun(root, required) as evidence:
        evidence.result.update(kind='native', gate='G1', engine=args.engine,
                               engine_started=False, phase='preflight_scene',
                               native_scope='in-progress: no promotion without every required measurement')
        evidence.save()
        process, probe, executor, log, metrics_log = None, None, None, None, None
        initialized = False
        checks, teardown = ({'unprofiled_acceptance':False} if profile_node else {}), {}
        phase_measurements = {}
        engine_members = {}
        observer_members = {}
        clock_members = {}
        clock_graph_passed = False
        dart_probe=None
        ownership_graph_single = False
        stopping = Event()
        previous = signal.signal(signal.SIGINT, lambda *_: stopping.set())
        try:
            repo = Path(__file__).resolve().parents[2]
            scene = load_scene(args.engine, args.scene_dir)
            if scene.get('dart_contact_mode','native')!=contact_mode:
                raise RuntimeError('requested DART mode does not match bound native scene')
            model = compile_model(Path(scene['robot']['path']).read_text())
            profile = CarryProfile(**json.loads(Path(args.profile).read_text()))
            swept_footprint(model, profile, profile.limits)
            evidence.result['phase'] = 'preflight_install'
            evidence.save()
            prefix, sensor = audit_runtime(repo, root)
            if contact_mode!='native':
                dart_probe=read_dart_contact_probe(prefix)
                save(root/'dart_contact_probe.json',dart_probe)
            no_existing_engines()
            if os.environ.get('LD_PRELOAD'):
                raise RuntimeError('unaccounted LD_PRELOAD; refusing native provenance ambiguity')
            command = ['ros2', 'launch', 'integrated_robot_navigation', 'crawl_system.launch.py',
                'engine:='+args.engine, 'navigation_scene:='+str(Path(args.scene_dir).resolve()),
                'carry_profile:='+str(Path(args.profile).resolve()), 'validation_mode:=true',
                'tf_provenance_output:='+str(root/'tf_provenance.jsonl'), *clock_arguments,*profile_arguments]
            evidence.result.update(command=command, model_sha256=model.model_sha256,
                execution_mode=dict(control_clock=clock_mode, validation_only=True,
                    dart_contact=contact_mode,
                    diagnostic_profile_node=profile_node,
                    crawl_clock_dispatch='isolated_2worker' if clock_mode == 'relay100' else 'single_worker'),
                config_sha256=profile.config_sha256, physics_sha256=profile.physics_sha256,
                native_physics_sha256=scene.get('native_physics_sha256'),
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
                        if executable.name == 'control_clock_relay' and pid not in clock_members:
                            clock_members[pid] = attest_control_clock(process, pid, sensor)
                            evidence.result['control_clock_members'] = list(clock_members.values())
                            evidence.save()
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
            if clock_mode == 'relay100':
                graph = dict(
                    source_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/clock')],
                    relay_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/navigation/control_clock')],
                    source_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/clock')],
                    relay_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/navigation/control_clock')])
                clock_graph_passed = assess_control_clock_graph(graph)
                save(root/'control_clock_graph.json', dict(graph=graph, passed=clock_graph_passed))
                if not clock_graph_passed or len(clock_members) != 1:
                    raise RuntimeError('control clock consumer scope or actual process ownership differs')
            checks['carry_measured_settle'] = True
            report = json.loads(call(probe.carry_report, Trigger.Request()).message)
            save(root/'action_results.json', report)
            checks['carry_terminal_received'] = carry_terminal(report)
            if args.engine == 'gazebo':
                save(root/'native_mapping.json', attest_gazebo_libraries(
                    process, list(engine_members.values()), sensor['gazebo_libraries'],dart_provider=dart_probe))
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
                    process, list(engine_members.values()), sensor['gazebo_libraries'],dart_provider=dart_probe))
        except BaseException as error:
            (root/'error_traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
            evidence.result['failure_phase'] = evidence.result['phase']
            evidence.fail(type(error).__name__+': '+str(error))
        finally:
            carry_owner_report = None
            if probe:
                probe.set_stage('shutdown', ignore_faults=True)
            if process and process.poll() is None and probe and executor:
                if clock_mode == 'relay100' and not (root/'control_clock_graph.json').exists():
                    graph = dict(
                        source_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/clock')],
                        relay_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/navigation/control_clock')],
                        source_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/clock')],
                        relay_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/navigation/control_clock')])
                    clock_graph_passed = assess_control_clock_graph(graph)
                    save(root/'control_clock_graph.json', dict(graph=graph, passed=clock_graph_passed,
                        scope='failure_diagnostic_not_startup_success'))
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
                def measured_stop():
                    response = call(probe.mode, SetMode.Request(mode='STOP'))
                    if not response.accepted:
                        raise RuntimeError('STOP mode request rejected: '+response.message)
                    wait(lambda: probe.motion.get('crawl', {}).get('stopped') is True, 3., 'shutdown measured stop')
                    return True

                def deactivate():
                    return call(probe.lifecycle, ChangeState.Request(
                        transition=Transition(id=Transition.TRANSITION_DEACTIVATE))).success

                def carry_terminal_stop():
                    response = call(probe.carry_stop, Trigger.Request())
                    if not response.success:
                        raise RuntimeError('carry stop rejected: '+response.message)
                    report = json.loads(call(probe.carry_report, Trigger.Request()).message)
                    save(root/'shutdown_action_results.json', report)
                    if report['pending_uuid'] is not None:
                        raise RuntimeError('shutdown action result remains unconfirmed')
                    return True  # no outstanding owner; not an assertion of successful grasp/action

                def native_stop():
                    response = call(probe.native_stop, Trigger.Request())
                    teardown['native_sensor_worker_joined'] = response.success
                    return response.success

                def consumers_stop():
                    teardown['runtime_stop'] = stop_runtime(process)
                    return teardown['runtime_stop']['confirmed']

                def clock_stop():
                    if len(clock_members) != 1:
                        raise RuntimeError('relay process identity missing')
                    before = call(probe.control_clock_report, Trigger.Request())
                    save(root/'control_clock_before_stop.json', json.loads(before.message))
                    stopped = call(probe.control_clock_stop, Trigger.Request())
                    teardown['control_clock_stop_ack'] = stopped.success
                    save(root/'control_clock_stop.json', json.loads(stopped.message))
                    for pid, member in clock_members.items():
                        if attest_control_clock(process,pid,sensor) != member:
                            raise RuntimeError('control clock PID/library changed before stop')
                        os.kill(pid, signal.SIGINT)
                    teardown['control_clock_exit_observed'] = wait_owned_members_exit(
                        process, list(clock_members), timeout=8.)
                    return stopped.success and teardown['control_clock_exit_observed']

                shutdown = shutdown_runtime_in_order(measured_stop=measured_stop,
                    deactivate=deactivate, carry_terminal=carry_terminal_stop,
                    native_stop=native_stop if args.engine == 'mujoco' else None,
                    consumers_stop=consumers_stop, clock_stop=clock_stop if clock_mode == 'relay100' else None)
                teardown.update(runtime_shutdown=shutdown, runtime_exit=shutdown['runtime_exit'])
                for error in shutdown['errors']:
                    evidence.fail('runtime stop/'+error['step']+': '+error['error'])
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
                        if teardown['engine_exit']:
                            teardown['launch_event_exit']=wait_launch_event_exit(process)
                            if not teardown['launch_event_exit']['confirmed']:
                                evidence.fail('engine exited but launch event completion unconfirmed')
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
                if contact_mode!='native':
                    assessment=assess_dart_contact_configuration(probe.native_controls,dart_probe)
                    save(root/'dart_contact_assessment.json',assessment)
                    checks['dart_contact_contract']=assessment['passed']
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
            if clock_mode == 'relay100':
                clock_codes = engine_returncodes(content, list(clock_members))
                teardown.update(control_clock_members=list(clock_members.values()),
                                control_clock_returncodes=clock_codes)
                try:
                    rows = [json.loads(line) for line in (root/'control_clock.jsonl').read_text().splitlines()]
                    assessment = assess_control_clock_trace(rows)
                except (OSError, ValueError) as error:
                    assessment = dict(passed=False, error=repr(error))
                save(root/'control_clock_assessment.json', assessment)
                checks['control_clock_contract'] = (assessment['passed'] and clock_graph_passed
                    and len(clock_members) == 1 and clock_codes == [0]
                    and teardown.get('control_clock_stop_ack') is True
                    and teardown.get('control_clock_exit_observed') is True)
            checks['tf_observer_owned'] = (len(observer_members) == 1 and observer_codes == [0])
            try:
                records = [json.loads(line) for line in (root/'tf_provenance.jsonl').read_text().splitlines()]
                checks['joint_tf_ownership'] = (ownership_graph_single and checks['tf_observer_owned']
                                               and assess_tf_ownership(records, model))
            except (OSError, ValueError):
                checks['joint_tf_ownership'] = False
            clean = (normal_teardown(teardown) and teardown.get('probe_receiver_joined') is True
                     and clean_shutdown([teardown], teardown.get('launch_returncode'), content))
            if clock_mode == 'relay100':
                clean = (clean and len(clock_members) == 1 and clock_codes == [0]
                    and teardown.get('control_clock_stop_ack') is True
                    and teardown.get('control_clock_exit_observed') is True)
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
    parser.add_argument('--control-clock-mode', choices=('native', 'relay100'), default='native')
    parser.add_argument('--dart-contact-mode',choices=('native','allowance50um'),default='native')
    parser.add_argument('--profile-node',choices=('motion_guard',),default=None,
                        help='owned main-thread diagnostic only; cannot pass G1 acceptance')
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
