#!/usr/bin/env python3
"""Serial native G1/G2 runner. Missing measurements stay FAIL, never candidate PASS."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict,replace
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
from lifecycle_msgs.msg import Transition,State
from lifecycle_msgs.srv import ChangeState,GetState
from std_srvs.srv import Trigger
from integrated_robot_interfaces.srv import SetMode
from integrated_robot_navigation.carry_profile import CarryProfile, G1_REQUIRED,G1_NATIVE_REQUIRED,swept_footprint,validate_profile
from integrated_robot_navigation.execution_contract import g2_execution_profile
from integrated_robot_navigation.acceptance_policy import calibration_timeout_s
from integrated_robot_navigation.g2_command_source import G2CommandSource,assess_command_trace
from split_observer_13_5 import SplitNavigationProbe
from integrated_robot_navigation.g2_sequence import movement_snapshot,run_sequence
from integrated_robot_navigation.dispatch_node import event_backend_manifest
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.load_process import assess_numeric_close,assess_numeric_jobs
from integrated_robot_navigation.runtime_cpu_probe import clock_sample,optional_thread_sample
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
from verify_navigation_13_5 import G2_REQUIRED,assess_crawl
from evidence_retention_13_5 import EvidenceBudget,maintain_trials


def make_native_probe(directory,*,engine,**kwargs):
    return SplitNavigationProbe(directory,engine=engine,**kwargs)


def finalize_evidence_retention(root):
    """Rotate storage after ownership ends, without changing original verdicts."""
    root=Path(root).resolve(strict=True)
    closed=json.loads((root/'teardown.json').read_text())
    if closed.get('parent_reaped') is not True or closed.get('residual_live_pids')!=[]:
        return dict(applied=False,reason='owned cleanup unconfirmed; evidence retained')
    result=maintain_trials(root.parent)
    return dict(applied=True,**result)


def run_with_retention(args):
    """Also finalize storage when the original acceptance run raised FAIL."""
    try:
        return run(args)
    finally:
        original_error=sys.exc_info()[0] is not None
        root=Path(args.output_dir)
        if (root/'teardown.json').is_file():
            try:
                save(root/'retention_rotation.json',finalize_evidence_retention(root))
            except Exception as error:
                save(root/'retention_error.json',dict(error=repr(error),original_error_preserved=original_error))
                if not original_error:raise


def save(path, value):
    # Full evaluated samples stay exact; indentation is not evidence. Avoid
    # the expanded pretty-print copy and its extra newline-sized allocation.
    # Serialize before opening so invalid numeric evidence cannot truncate an
    # existing result. Small verdict/provenance files keep their old bytes.
    bulk=path.name in ('frames.json','all_frames.json','native_controls.json')
    encoded=(json.dumps(value,separators=(',',':'),allow_nan=False) if bulk else
        json.dumps(value,indent=2,allow_nan=False))
    with path.open('w',encoding='utf-8') as stream:
        stream.write(encoded);stream.write('\n')


@contextmanager
def teardown_checkpoint(path):
    """Persist partial facts even if cleanup raises; exception remains a failure."""
    state=dict(finalization_complete=False)
    try:yield state
    finally:save(path,state)


def crawl_dispatch_mode(engine,clock_mode,is_g2):
    if clock_mode=='native':return 'single_worker'
    return 'direct_single_owner'


def capture_native_command_trace(engine, *, call, client, path):
    """Keep the original large reply; conversion waits for engine/receiver join."""
    if engine=='gazebo':return False  # this service belongs to the MuJoCo plugin
    if engine!='mujoco':raise ValueError('unknown command trace engine')
    response=call(client,Trigger.Request(),seconds=10.)
    if response.success is not True:raise RuntimeError('native command trace freeze/export failed')
    with path.open('x',encoding='utf-8') as output:output.write(response.message)
    return True


def capture_native_worker_stop(response,path):
    """Preserve the small original join reply; an ACK alone proves no exit."""
    with path.open('x',encoding='utf-8') as output:output.write(response.message)
    if response.success is not True or len(response.message)>4096:return False
    try:
        value=json.loads(response.message)
        if (not isinstance(value,dict) or value.get('sensor_worker_joined') is not True
                or value.get('applied_worker_joined') is not True
                or value.get('engine_exit_acknowledgment') is not False):return False
        counts=[value.get(key) for key in ('applied_submitted','applied_published',
            'applied_overwritten','applied_dropped_busy')]
        return (all(type(count) is int and count>=0 for count in counts)
            and counts[1]+counts[2]==counts[0])
    except (ValueError,TypeError):return False


def validate_native_command_trace(path, *, parent_reaped, receivers_joined):
    if not parent_reaped or not receivers_joined:
        raise RuntimeError('native trace decoding requires parent reap and all receiver joins')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict) or value.get('schema')!=1 or value.get('frozen') is not True:
        raise ValueError('native command trace schema/freeze')
    names=value.get('joints')
    if (not isinstance(names,list) or not 1<=len(names)<=64 or
            any(not isinstance(n,str) or not n for n in names) or len(set(names))!=len(names)):
        raise ValueError('native command trace joint mapping')
    counts={}
    for lane,cap in (('cm_write',2000),('pre_step',6000)):
        rows=value.get(lane,{}).get('rows')
        if not isinstance(rows,list) or not 1<=len(rows)<=cap:
            raise ValueError('native command trace row capacity/missing')
        for row in rows:
            for field in ('ctrl','joint_velocity'):
                data=row.get(field)
                if (not isinstance(data,list) or len(data)!=len(names) or
                        any(type(n) not in (int,float) or not math.isfinite(n) for n in data)):
                    raise ValueError('native command trace shape/nonfinite')
            if (type(row.get('steady_ns')) is not int or row['steady_ns']<=0 or
                    type(row.get('snapshot_ros_ns')) is not int or row['snapshot_ros_ns']<0):
                raise ValueError('native command trace original clock')
        counts[lane]=len(rows)
    return dict(passed=True,scope='post_reap_and_receiver_join_diagnostic_validation_not_gate_success',
        rows=counts,sha256=file_digest(path))


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


def g2_required_checks(clock_mode,contact_mode,engine,scenario):
    if scenario not in ('crawl-cycle','crawl-reverse'):raise ValueError('unknown G2 scenario')
    # Calibration-only checks are inherited by verified G1, not relabelled as
    # newly measured calibration during a moving sequence.
    required=(native_required_checks(clock_mode,contact_mode,engine)
        -{'unvalidated_crawl_rejected','contact_lift'}) | {
        'g1_profile_verified','crawl_admission_accepted','bounded_test_commands','command_source_shutdown'}
    if engine=='gazebo':required=required|{'numeric_worker_normal_close','numeric_worker_job_contract'}
    return required | (G2_REQUIRED if scenario=='crawl-cycle' else FRAME_REQUIRED|{'stand10','reverse','stopped'})


def prepare_g2_profile(profile,model,engine,scene,clock_mode,result_path,current_source,current_install):
    if result_path is None:raise ValueError('actual G1 result required before G2 engine start')
    path=Path(result_path).resolve(strict=True)
    execution=g2_execution_profile(scene,clock_mode)
    candidate=replace(profile,state='native_validated',native_evidence={engine:dict(path=str(path),sha256=file_digest(path))})
    accepted,reason=validate_profile(candidate,model,engine,execution_profile=execution)
    if not accepted:raise ValueError('G2 G1 proof rejected: '+reason)
    source=json.loads((path.parent/'source_manifest.json').read_text())
    installed=json.loads((path.parent/'install_manifest.json').read_text())
    if source.get('files')!=current_source.get('files') or installed!=current_install:
        raise ValueError('G2 requires the same fixed runtime sources and selected installation as G1')
    return candidate,execution


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


def assess_dart_contact_configuration(records,expected,*,scenario='sensors-carry'):
    report=dict(scope='native_api_configuration_not_contact_task_success',passed=False,records=len(records))
    try:
        phases_required={
            'sensors-carry':{'stand','calibrate'},
            'crawl-cycle':{'stand','forward','left','right','stopped'},
            'crawl-reverse':{'stand','reverse','stopped'},
            'contact-component':{'stand','forward','stopped'},
        }[scenario]
        report['required_phases']=sorted(phases_required)
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
        if not phases_required<=phases:raise ValueError('missing operational DART setting witnesses')
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
    consumers = {'motion_guard', 'crawl_controller_ingress', 'carry_manager', 'nav_projection', 'crawl_startup'}
    return (len(graph.get('source_publishers', [])) == 1
        and graph.get('relay_publishers') == ['navigation_control_clock']
        and len(graph.get('relay_subscribers', [])) == 5
        and set(graph['relay_subscribers']) == consumers
        and not (consumers|{'crawl_controller'}).intersection(graph.get('source_subscribers', []))
        and 'navigation_control_clock' in graph.get('source_subscribers', []))


def assess_control_clock_writer(state,rows):
    result=dict(passed=False,scope='actual_file_worker_drain_and_join_not_clock_or_engine_proof')
    try:
        if (state['scope']!='bounded_file_worker_no_ROS_clock_or_commands'
                or any(state[key] is not True for key in ('closed','joined','drained'))
                or state['in_flight'] is not False or state['error']!=''):
            raise ValueError('writer lifetime/failure unconfirmed')
        keys=('capacity','maximum_bytes','accepted','written','pending_records','pending_bytes','peak_records','peak_bytes')
        if any(type(state[key]) is not int or state[key]<0 for key in keys):
            raise ValueError('writer counters invalid')
        if (state['capacity']!=128 or state['maximum_bytes']!=4194304
                or state['accepted']!=len(rows) or state['written']!=len(rows)
                or state['pending_records']!=0 or state['pending_bytes']!=0
                or not 0<state['peak_records']<=state['capacity']
                or not 0<state['peak_bytes']<=state['maximum_bytes']):
            raise ValueError('writer work missing or exceeds fixed bounds')
        result.update(passed=True,state=state)
    except (KeyError,TypeError,ValueError) as error:result['error']=str(error)
    return result


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


def attest_crawl_ingress(process,snapshot,entrypoint,*,proc_root=Path('/proc'),
                         expected_dispatch='owned_serial_waitset'):
    """Bind the clock subscriber to the existing live owned CRAWL process.

    This supplements the exact-five graph check, never proves engine exit.
    """
    try:
        pid,tid=snapshot['pid'],snapshot['native_tid']
        if (type(pid) is not int or type(tid) is not int or min(pid,tid)<=0 or pid==tid
                or snapshot['uid']!=os.getuid() or snapshot['node_name']!='crawl_controller_ingress'
                or expected_dispatch not in ('owned_serial_waitset','owned_serial_events')
                or snapshot['namespace']!='/' or snapshot['dispatch']!=expected_dispatch
                or snapshot['alive'] is not True or snapshot['joined'] is not False
                or snapshot['error'] is not None
                or snapshot['clock_subscriptions']!=['/navigation/control_clock']):
            raise ValueError('receiver role or lifetime differs')
        if expected_dispatch=='owned_serial_events':
            if (snapshot.get('executor_type')!='EventsExecutor'
                    or snapshot.get('backend_manifest')!=event_backend_manifest()):
                raise ValueError('receiver event dependency differs')
        directory=proc_root/str(pid);identity=process_identity(pid,proc_root=proc_root)
        entrypoint=Path(entrypoint).resolve(strict=True);digest=file_digest(entrypoint)
        arguments=(directory/'cmdline').read_bytes().split(b'\0')[:2]
        if (directory.stat().st_uid!=os.getuid() or identity['ppid']!=process.pid
                or identity['pgid']!=process.pid
                or (directory/'task'/str(tid)).stat().st_uid!=os.getuid()
                or entrypoint not in [Path(os.fsdecode(arg)).resolve(strict=True) for arg in arguments if arg]):
            raise ValueError('owned process, thread or installed entrypoint differs')
        if process_identity(pid,proc_root=proc_root)!=identity or file_digest(entrypoint)!=digest:
            raise ValueError('receiver identity changed during observation')
        return dict(**identity,native_tid=tid,node_name=snapshot['node_name'],
            entrypoint=str(entrypoint),entrypoint_sha256=digest,receiver=snapshot,
            scope='live_owned_crawl_ingress_not_exit_proof')
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise RuntimeError('crawl ingress ownership unconfirmed: '+str(error)) from error


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
    evidence_observer=(sensors/'lib/integrated_robot_navigation_sensors/navigation_evidence_recorder').resolve(strict=True)
    if not evidence_observer.is_relative_to(sensors.resolve()):
        raise RuntimeError('native evidence observer outside selected sensor prefix')
    sensor_probe['evidence_observer']=dict(path=str(evidence_observer),sha256=file_digest(evidence_observer))
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


def deactivate_crawl_if_active(*,call,state_client,transition_client,report_client):
    """Release lifecycle ownership without sending an invalid transition.

    An inactive node does not prove physical stopping. That separate required
    shutdown stage is never inferred from this result.
    """
    before=call(state_client,GetState.Request()).current_state.id
    stable={State.PRIMARY_STATE_UNCONFIGURED,State.PRIMARY_STATE_INACTIVE,
            State.PRIMARY_STATE_ACTIVE,State.PRIMARY_STATE_FINALIZED}
    if before not in stable:raise RuntimeError('crawl lifecycle state is not stable: '+str(before))
    response=call(report_client,Trigger.Request())
    if response.success is not True:raise RuntimeError('crawl active-state report rejected')
    owner=json.loads(response.message)
    if not isinstance(owner,dict) or owner.get('active') is not (before==State.PRIMARY_STATE_ACTIVE):
        raise RuntimeError('crawl lifecycle state and active owner differ')
    sent=before==State.PRIMARY_STATE_ACTIVE
    if sent:
        changed=call(transition_client,ChangeState.Request(
            transition=Transition(id=Transition.TRANSITION_DEACTIVATE)))
        if changed.success is not True:raise RuntimeError('crawl deactivation rejected')
    after=call(state_client,GetState.Request()).current_state.id
    response=call(report_client,Trigger.Request())
    if (after!=(State.PRIMARY_STATE_INACTIVE if sent else before)
            or response.success is not True or json.loads(response.message).get('active') is not False):
        raise RuntimeError('crawl lifecycle release state unconfirmed')
    return dict(success=True,state_before=before,state_after=after,transition_sent=sent,
        scope='lifecycle_release_not_measured_stop')


def shutdown_runtime_in_order(*, measured_stop, deactivate, carry_terminal, consumers_stop,
                              native_stop=None, clock_stop=None,numeric_stop=None):
    """Preserve failed safety stages, still release consumers before their clock.

    No retries, synthetic terminal results, or false normal-exit substitution.
    Engine shutdown/parent exit status remain separate caller responsibilities.
    """
    steps, errors = {}, []
    for name, operation in (('measured_stop',measured_stop), ('deactivate',deactivate),
            ('carry_terminal',carry_terminal), ('numeric_stop',numeric_stop),('native_stop',native_stop),
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
    if args.scenario not in ('sensors-carry','crawl-cycle','crawl-reverse'):raise ValueError('unknown native scenario')
    is_g2=args.scenario!='sensors-carry'
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=False)
    storage_budget=EvidenceBudget(root)
    clock_mode = getattr(args, 'control_clock_mode', 'native')
    contact_mode=getattr(args,'dart_contact_mode','native')
    profile_node=getattr(args,'profile_node',None)
    required=(g2_required_checks(clock_mode,contact_mode,args.engine,args.scenario) if is_g2 else
        native_required_checks(clock_mode,contact_mode,args.engine,profile_node=profile_node))
    clock_arguments = control_clock_launch_arguments(clock_mode, root)
    profile_arguments=g1_profile_arguments(profile_node,root)
    with EvidenceRun(root, required) as evidence, teardown_checkpoint(root/'teardown.json') as teardown:
        evidence.result.update(kind='native', gate='G2' if is_g2 else 'G1',engine=args.engine,
                               engine_started=False, phase='preflight_scene',
                               native_scope='in-progress: no promotion without every required measurement')
        evidence.result['evidence_policy']=dict(raw_byte_limit=storage_budget.raw_bytes,
            working_byte_limit=storage_budget.working_bytes,wall_limit_s=storage_budget.wall_seconds,
            retained_sample_hz=2,ordinary_raw='temporary_until_full_assessment_then_latest_representatives',
            limit_failure='normal_cleanup_and_FAIL_never_drop_to_PASS')
        evidence.save()
        process, probe, executor, log, metrics_log = None, None, None, None, None
        source_node,source_executor=None,None
        source_joined=source_stop_ok=False
        initialized = False
        checks = {'unprofiled_acceptance':False} if profile_node else {}
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
            # Startup/exit are the automatic retention checkpoints. They never
            # run inside live control callbacks or the current assessment.
            no_existing_engines()
            save(root/'pre_run_retention.json',maintain_trials(root.parent))
            if is_g2 and (not getattr(args,'g1_result',None) or profile_node is not None):
                raise ValueError('G2 requires actual G1 evidence and an unprofiled execution')
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
            profile_path=str(Path(args.profile).resolve())
            execution_profile=None
            if is_g2:
                profile,execution_profile=prepare_g2_profile(profile,model,args.engine,scene,clock_mode,
                    args.g1_result,json.loads((root/'source_manifest.json').read_text()),
                    json.loads((root/'install_manifest.json').read_text()))
                profile_path=str(root/'validated_profile.json')
                save(Path(profile_path),asdict(profile))
                checks['g1_profile_verified']=True
            if contact_mode!='native':
                dart_probe=read_dart_contact_probe(prefix)
                save(root/'dart_contact_probe.json',dart_probe)
            no_existing_engines()
            if os.environ.get('LD_PRELOAD'):
                raise RuntimeError('unaccounted LD_PRELOAD; refusing native provenance ambiguity')
            command = ['ros2', 'launch', 'integrated_robot_navigation', 'crawl_system.launch.py',
                'engine:='+args.engine, 'navigation_scene:='+str(Path(args.scene_dir).resolve()),
                'carry_profile:='+profile_path, 'validation_mode:=true',
                'tf_provenance_output:='+str(root/'tf_provenance.jsonl'), *clock_arguments,*profile_arguments]
            if is_g2:command.append('g2_validation_mode:=true')
            evidence.result.update(command=command, model_sha256=model.model_sha256,
                execution_mode=dict(control_clock=clock_mode, validation_only=True,
                    observer_backend=getattr(args,'observer_backend','python'),
                    g2_validation_mode=is_g2,native_execution_profile=execution_profile,
                    dart_contact=contact_mode,
                    diagnostic_profile_node=profile_node,
                    crawl_clock_dispatch=crawl_dispatch_mode(args.engine,clock_mode,is_g2)),
                config_sha256=profile.config_sha256, physics_sha256=profile.physics_sha256,
                native_physics_sha256=scene.get('native_physics_sha256'),
                scene=scene, thread_diagnostics=bool(getattr(args,'thread_diagnostics',False)),
                environment={key: os.environ.get(key) for key in (
                    'ROS_DOMAIN_ID', 'MUJOCO_GL', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'LP_NUM_THREADS')})
            evidence.save()
            rclpy.init(args=[], signal_handler_options=SignalHandlerOptions.NO)
            initialized = True
            # Both acceptance gates need lossless recording without coupling
            # native ingress to filesystem latency (G1 76473ca6 is the RED).
            probe = make_native_probe(root, engine=args.engine,
                observer_backend=getattr(args,'observer_backend','python'))
            executor = ProbeReceiver(probe)
            evidence.result['probe_receiver']=dict(executor=type(executor.executor).__name__,
                serial_callbacks=True,owner=process_identity(os.getpid()),
                callback_thread_tid=executor.thread.native_id,
                dependency_files=event_backend_manifest())
            evidence.result['full_observer_process']=probe.observer.identity
            if getattr(args,'observer_backend','python')=='native_cdr':
                expected=sensor['evidence_observer']
                if (probe.observer.identity['executable']!=expected['path']
                        or probe.observer.identity['executable_sha256']!=expected['sha256']):
                    raise RuntimeError('actual native evidence observer differs from selected installation')
            if is_g2:
                source_node=G2CommandSource(profile.limits,trace_path=root/'g2_commands.jsonl')
                source_executor=ProbeReceiver(source_node)
                evidence.result['test_command_source']=dict(kind='bounded_fixture_not_Nav2_or_PPO',
                    identity=process_identity(os.getpid()),topics=['/navigation/cmd_vel_raw','/navigation/cmd_vel_smoothed'])
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
                    storage_budget.check()
                    rows = []
                    for pid in members:
                        try:
                            row = process_metrics(pid, process.pid)
                            argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
                            row['executable'] = ' '.join(os.fsdecode(value) for value in argv[:2])
                            if row['executable'].startswith('gz sim ') or row['executable'].endswith('/crawl_controller'):
                                row['thread_work']=optional_thread_sample(pid,process.pid,row['start_ticks'],
                                    enabled=getattr(args,'thread_diagnostics',False))
                            rows.append(row)
                        except (OSError, ValueError, IndexError):
                            continue  # raced a normal owned process exit; never sample a replacement
                    observer=process_metrics(os.getpid(),os.getpgrp())
                    observer['scope']='runner_mission_and_test_command_source'
                    identity=probe.observer.identity
                    full_observer=process_metrics(identity['pid'],identity['pgid'])
                    if full_observer['start_ticks']!=identity['start_ticks']:
                        raise RuntimeError('full observer CPU identity changed')
                    metrics_log.write(json.dumps(dict(**clock_sample(),members=rows,observer=observer,
                        full_observer=full_observer))+'\n')
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
                if source_executor is not None and not probe.ignore_faults:source_executor.check()
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
                ingress_report=call(probe.crawl_report,Trigger.Request())
                if ingress_report.success is not True:
                    raise RuntimeError('crawl ingress ownership report rejected')
                save(root/'control_clock_ingress_report.json',json.loads(ingress_report.message))
                ingress_owner=attest_crawl_ingress(process,
                    json.loads(ingress_report.message)['ingress_dispatch'],
                    prefix/'integrated_robot_navigation/lib/integrated_robot_navigation/crawl_controller',
                    expected_dispatch=('owned_serial_events' if is_g2 or args.engine=='gazebo'
                        else 'owned_serial_waitset'))
                save(root/'control_clock_ingress_owner.json',ingress_owner)
                graph = dict(
                    source_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/clock')],
                    relay_publishers=[row.node_name for row in probe.get_publishers_info_by_topic('/navigation/control_clock')],
                    source_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/clock')],
                    relay_subscribers=[row.node_name for row in probe.get_subscriptions_info_by_topic('/navigation/control_clock')])
                clock_graph_passed = (assess_control_clock_graph(graph)
                    and graph['relay_subscribers'].count(ingress_owner['node_name'])==1)
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
            if not is_g2:
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
            if is_g2:
                def snapshot():
                    return probe.movement_decision(profile.limits)
                def move_stage(name):
                    probe.set_stage(name);evidence.result['phase']='g2_'+name;evidence.save()
                def request_mode(name):return call(probe.mode,SetMode.Request(mode=name)).accepted is True
                phase_measurements.update(run_sequence(args.scenario,snapshot=snapshot,source=source_node,
                    mode=request_mode,wait=wait,set_stage=move_stage,limits=profile.limits))
                checks['crawl_admission_accepted']=True
            else:
                probe.set_stage('calibrate')
                evidence.result['phase'] = 'contact_calibration'
                evidence.save()
                calibration_ros, calibration_wall = probe.get_clock().now().nanoseconds, time.monotonic_ns()
                calibration = call(probe.calibrate, Trigger.Request())
                if not calibration.success:
                    raise RuntimeError('owned contact calibration rejected: '+calibration.message)
                wait(lambda: probe.motion.get('crawl', {}).get('state') == 'CALIBRATING', 2., 'calibration start')
                wait(lambda: probe.motion.get('crawl', {}).get('state') == 'STAND'
                     and probe.motion['crawl']['stopped'], calibration_timeout_s(profile.limits), 'measured calibration landing/settle')
                phase_measurements['calibration'] = dict(start_ros_ns=calibration_ros, start_wall_ns=calibration_wall,
                    ros_duration_s=(probe.get_clock().now().nanoseconds-calibration_ros)/1e9,
                    wall_duration_s=(time.monotonic_ns()-calibration_wall)/1e9,
                    wall_budget_s=calibration_timeout_s(profile.limits), acceptance_policy='book_v1')
            evidence.result['phase'] = 'owner_attestation'
            evidence.save()
            graph = probe.owner_graph(include_command_sources=is_g2)
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
            if source_node is not None:
                try:
                    source_node.stop('runner_shutdown');source_stop_ok=True
                except Exception as error:evidence.fail('G2 command stop: '+repr(error))
                if source_executor is not None:
                    source_joined=source_executor.shutdown(timeout_sec=2.)
                    if source_executor.error is not None:
                        evidence.fail('G2 command receiver: '+repr(source_executor.error))
                teardown['command_source_joined']=source_joined
                save(root/'g2_command_source.json',source_node.report())
            if probe:
                try:probe.set_stage('shutdown', ignore_faults=True)
                except Exception as error:evidence.fail('observer shutdown stage: '+repr(error))
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
                if args.engine=='gazebo':
                    try:
                        report=call(probe.contact_adapter_report,Trigger.Request())
                        if not report.success:raise RuntimeError('contact adapter report rejected')
                        save(root/'contact_adapter_report.json',json.loads(report.message))
                    except Exception as error:
                        evidence.fail('contact adapter boundary capture: '+repr(error))
                def measured_stop():
                    response = call(probe.mode, SetMode.Request(mode='STOP'))
                    if not response.accepted:
                        raise RuntimeError('STOP mode request rejected: '+response.message)
                    wait(lambda: probe.motion.get('crawl', {}).get('stopped') is True, 3., 'shutdown measured stop')
                    return True

                def deactivate():
                    result=deactivate_crawl_if_active(call=call,state_client=probe.lifecycle_state,
                        transition_client=probe.lifecycle,report_client=probe.crawl_report)
                    save(root/'shutdown_lifecycle_release.json',result)
                    return result['success']

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
                    try:
                        teardown['native_command_trace_captured']=capture_native_command_trace(args.engine,
                            call=call,client=probe.native_command_trace,path=root/'native_command_trace.json')
                    except Exception as error:
                        evidence.fail('native command trace: '+repr(error))
                        # A diagnostic failure must not skip the original worker stop.
                    response = call(probe.native_stop, Trigger.Request())
                    joined=capture_native_worker_stop(response,root/'native_worker_stop_reply.json')
                    teardown['native_worker_stop_ack_valid']=joined
                    teardown['native_sensor_worker_joined']=joined
                    teardown['applied_reference_worker_joined']=joined
                    return joined

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

                def numeric_stop():
                    reply=call(probe.numeric_stop,Trigger.Request())
                    record=json.loads(reply.message)
                    save(root/'numeric_worker_close.json',record)
                    checks['numeric_worker_normal_close']=(reply.success is True
                        and assess_numeric_close(record,model.model_sha256))
                    checks['numeric_worker_job_contract']=assess_numeric_jobs(record)
                    return checks['numeric_worker_normal_close']

                shutdown = shutdown_runtime_in_order(measured_stop=measured_stop,
                    deactivate=deactivate, carry_terminal=carry_terminal_stop,
                    numeric_stop=numeric_stop if is_g2 and args.engine=='gazebo' else None,
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
                teardown['probe_receivers']=executor.report()
                if not teardown['probe_receiver_joined']:
                    raise RuntimeError('probe callback not joined; ROS handles and log retained')
            if probe:
                # Runtime/engine have stopped and receiver callbacks joined.
                # Restore ALL original records; never assess only the live cache.
                try:
                    probe.restore_history(receiver_joined=teardown.get('probe_receiver_joined') is True)
                    history_ready=True
                except (OSError,ValueError,RuntimeError,KeyError) as error:
                    history_ready=False
                    evidence.fail('observation journal restoration: '+repr(error))
                finally:
                    teardown['full_observer_process']=probe.observer.report()
                    if teardown['full_observer_process']['runtime_fault']:
                        evidence.fail('full observer runtime fault: '+str(teardown['full_observer_process']['runtime_fault']))
                    teardown['probe_receiver_joined']=(teardown.get('probe_receiver_joined') is True
                        and teardown['full_observer_process']['joined'] is True
                        and teardown['full_observer_process']['exitcode']==0
                        and not teardown['full_observer_process']['error'])
                if args.engine=='mujoco' and teardown.get('native_command_trace_captured'):
                    try:
                        save(root/'native_command_trace_validation.json',validate_native_command_trace(
                            root/'native_command_trace.json',parent_reaped=teardown.get('parent_reaped') is True,
                            receivers_joined=(history_ready and teardown.get('probe_receiver_joined') is True
                                and (not is_g2 or source_joined))))
                    except (OSError,ValueError,RuntimeError,TypeError,AttributeError) as error:
                        evidence.fail('post-join native command trace validation: '+repr(error))
            if probe and history_ready:
                save(root/'native_controls.json', dict(kind='native_observations_not_command_topics',
                    records=probe.native_controls, diagnostic_errors=probe.transport_errors))
                observations = dict(root_source='native_ground_truth', urdf=model.urdf,
                    frames=operational_frames(probe.frames), phases=phase_measurements)
                if is_g2:
                    observations['stopped_frames']=[row for row in probe.frames if row['stage']=='stopped']
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
                checks.update(assess_crawl(observations,profile.limits,scenario=args.scenario) if is_g2 else
                    assess_frames(observations, profile.limits))
                sensor_report = assess_g1_sensors(observations, Path(scene['world']['path']).read_text(), args.engine)
                if is_g2:
                    sensor_report['scope']='G2 stand/IMU/frames; calibration lift inherited through verified G1'
                    checks.update({key:value for key,value in sensor_report['checks'].items() if key!='contact_lift'})
                else:checks.update(sensor_report['checks'])
                save(root/('g2_sensor_assessment.json' if is_g2 else 'g1_sensor_assessment.json'),sensor_report)
                carry_report = assess_carry_admission(observations, profile.arm_q, carry_owner_report)
                save(root/'carry_hold_assessment.json', carry_report)
                checks['carry_measured_settle'] = (checks.get('carry_measured_settle') is True
                                                  and carry_report['passed'])
                control_stages={'stand','calibrate'}|({'forward','left','right','reverse','stopped'} if is_g2 else set())
                measured_controls=[row for row in probe.native_controls if row['stage'] in control_stages]
                if args.engine == 'mujoco':
                    checks['native_ctrl_observed'] = (checks.get('native_library_loaded') is True
                        and not probe.transport_errors and assess_native_controls(
                            measured_controls,
                            model, Path(scene['world']['path']).read_text()))
                else:
                    control_report = {}
                    measured = assess_gazebo_controls(
                        measured_controls,
                        model,Path(scene['world']['path']).read_text(),report=control_report)
                    save(root/'native_controls_assessment.json',control_report)
                    checks['native_ctrl_observed'] = (checks.get('native_library_loaded') is True
                        and not probe.transport_errors and measured)
                save(root/'probe_diagnostics.json', dict(errors=probe.errors, missing=dict(probe.missing),
                    final_states=probe.motion, all_frames=len(probe.frames), tf_python_api=probe.tf_api,
                    transport_errors=probe.transport_errors,observer_timing=probe.timing_snapshot()))
                if contact_mode!='native':
                    assessment=assess_dart_contact_configuration(
                        probe.native_controls,dart_probe,scenario=args.scenario)
                    save(root/'dart_contact_assessment.json',assessment)
                    checks['dart_contact_contract']=assessment['passed']
            if source_node is not None:
                if not source_joined:
                    raise RuntimeError('G2 command worker not joined; ROS handles retained; next engine forbidden')
                source_node.destroy_node()
                checks['command_source_shutdown']=(source_stop_ok and source_executor.error is None)
                try:
                    command_rows=[json.loads(line) for line in (root/'g2_commands.jsonl').read_text().splitlines()]
                    command_report=assess_command_trace(command_rows,profile.limits)
                    save(root/'g2_command_assessment.json',command_report)
                    checks['bounded_test_commands']=command_report['passed']
                except (OSError,ValueError,TypeError) as error:
                    evidence.fail('G2 command trace: '+repr(error))
            if probe:
                try:probe.close_log()
                except (OSError,ValueError,RuntimeError) as error:
                    evidence.fail('observation journal close: '+repr(error))
                if probe.journal is not None:
                    writer_report=probe.journal.report()
                    writer_report['first_failure']=probe.journal_failure
                    save(root/'journal_writer.json',writer_report)
                    teardown['journal_writer_joined']=writer_report['joined']
                    if not writer_report['joined']:
                        raise RuntimeError('observation writer not joined; ROS resources retained; next engine forbidden')
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
                    writer = assess_control_clock_writer(
                        json.loads((root/'control_clock.jsonl.writer.json').read_text()),rows)
                    assessment['writer']=writer
                    assessment['passed']=assessment['passed'] and writer['passed']
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
            if is_g2:clean=clean and checks.get('command_source_shutdown') is True
            if clock_mode == 'relay100':
                clean = (clean and len(clock_members) == 1 and clock_codes == [0]
                    and assessment['passed']
                    and teardown.get('control_clock_stop_ack') is True
                    and teardown.get('control_clock_exit_observed') is True)
            checks.update(normal_runtime_exit=clean and teardown.get('runtime_exit') is True,
                normal_engine_exit=clean and teardown.get('engine_exit') is True,
                parent_reaped=teardown.get('parent_reaped') is True,
                no_residual_members=teardown.get('residual_live_pids') == [])
            teardown['finalization_complete']=True
            save(root/'teardown.json', teardown)
            try:
                save(root/'evidence_budget.json',storage_budget.check())
            except RuntimeError as error:
                evidence.fail(str(error))
                save(root/'evidence_budget.json',dict(passed=False,error=str(error)))
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
    parser.add_argument('--g1-result',help='G2 only: actual matching fixed-source G1 result; never a ready flag')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--control-clock-mode', choices=('native', 'relay100'), default='native')
    parser.add_argument('--dart-contact-mode',choices=('native','allowance50um'),default='native')
    parser.add_argument('--observer-backend',choices=('python','native_cdr'),default='python',
        help='explicit read-only CDR witness; original ages and required checks remain unchanged')
    parser.add_argument('--profile-node',choices=('motion_guard',),default=None,
                        help='owned main-thread diagnostic only; cannot pass G1 acceptance')
    parser.add_argument('--thread-diagnostics',action='store_true',
                        help='opt-in costly read-only per-thread procfs scan; not an acceptance witness')
    args = parser.parse_args()
    run_with_retention(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
