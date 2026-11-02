"""Breaks: test mode silently changes defaults, accepts fabricated/fast clocks,
or declares clean shutdown without a final stopped relay and source identity.
"""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
import os
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[4]/'scripts'))
import run_navigation_13_5 as runner


def test_clock_arguments_are_explicit_and_native_remains_default(tmp_path):
    assert hasattr(runner, 'control_clock_launch_arguments'), 'relay execution mode binding missing'
    assert runner.control_clock_launch_arguments('native', tmp_path) == []
    assert runner.control_clock_launch_arguments('relay100', tmp_path) == [
        'control_clock_mode:=relay100', 'control_clock_output:='+str(tmp_path/'control_clock.jsonl')]
    with pytest.raises(ValueError):
        runner.control_clock_launch_arguments('fast', tmp_path)


def good_rows():
    return [dict(event='publish', capture_ns=123000000010, sec=123, nanosec=10,
                 received_wall_ns=1000000000, published_wall_ns=1001000000,
                 gid='a', inputs=5, outputs=1),
            dict(event='armed', wall_ns=1005000000,
                 report=dict(mode='relay100', fault='', closing=False, armed=True, inputs=5,
                     outputs=1, gid='a', last_source_capture_ns=123000000010,
                     last_source_receipt_ns=1000000000)),
            dict(event='publish', capture_ns=123000000020, sec=123, nanosec=20,
                 received_wall_ns=1010000000, published_wall_ns=1011000000,
                 gid='a', inputs=10, outputs=2),
            dict(event='closed', wall_ns=1020000000,
                 report=dict(mode='relay100', fault='', closing=True, armed=True, inputs=10, outputs=2, gid='a'))]


def test_clock_assessor_accepts_original_values_not_synthetic_time():
    assert hasattr(runner, 'assess_control_clock_trace'), 'producer trace safety assessment missing'
    report = runner.assess_control_clock_trace(good_rows())
    assert report['passed'] and report['publications'] == 2
    assert report['scope'] == 'producer_trace_not_independent_wire_proof'


def test_clock_assessor_denies_unarmed_run_even_if_publications_are_valid():
    rows = [row for row in good_rows() if row['event'] != 'armed']
    assert not runner.assess_control_clock_trace(rows)['passed'], 'unarmed bootstrap is not operational acceptance'


@pytest.mark.parametrize('mutation', ['retag', 'too_fast', 'stale', 'rollback', 'gid',
                                     'missing_close', 'fault', 'after_close', 'count'])
def test_clock_assessor_rejects_each_failed_contract(mutation):
    assert hasattr(runner, 'assess_control_clock_trace'), 'producer trace safety assessment missing'
    rows = deepcopy(good_rows())
    second = [row for row in rows if row['event'] == 'publish'][1]
    if mutation == 'retag': second['capture_ns'] += 1
    elif mutation == 'too_fast': second['published_wall_ns'] -= 1
    elif mutation == 'stale': second['received_wall_ns'] = 1
    elif mutation == 'rollback':
        second.update(capture_ns=123000000000, sec=123, nanosec=0)
    elif mutation == 'gid': second['gid'] = 'b'
    elif mutation == 'missing_close': rows.pop()
    elif mutation == 'fault': rows[-1]['report']['fault'] = 'source_stalled'
    elif mutation == 'after_close': rows += [rows[0]]
    elif mutation == 'count': rows[-1]['report']['outputs'] = 3
    assert not runner.assess_control_clock_trace(rows)['passed']


@pytest.mark.parametrize('bad', ['duplicate_arm', 'stale_arm', 'closed_arm', 'no_positive', 'wrong_gid'])
def test_clock_arm_record_requires_one_fresh_open_original_source(bad):
    rows = good_rows()
    arm = rows[1]
    if bad == 'duplicate_arm': rows.insert(1, deepcopy(arm))
    elif bad == 'stale_arm': arm['report']['last_source_receipt_ns'] = 1
    elif bad == 'closed_arm': arm['report']['closing'] = True
    elif bad == 'no_positive': arm['report']['last_source_capture_ns'] = 0
    elif bad == 'wrong_gid': arm['report']['gid'] = 'b'
    assert not runner.assess_control_clock_trace(rows)['passed']


def test_clock_graph_rejects_unintended_consumers_or_original_clock_leak():
    assert hasattr(runner, 'assess_control_clock_graph'), 'five-node graph boundary assessment missing'
    consumers = ['motion_guard', 'crawl_controller_ingress', 'carry_manager', 'nav_projection', 'crawl_startup']
    graph = dict(source_publishers=['engine'], relay_publishers=['navigation_control_clock'],
                 source_subscribers=['navigation_control_clock', 'probe', 'robot_state_publisher'],
                 relay_subscribers=consumers)
    assert runner.assess_control_clock_graph(graph)
    for key, extra in [('source_subscribers', 'motion_guard'),
                       ('relay_subscribers', 'robot_state_publisher'),
                       ('relay_publishers', 'foreign')]:
        bad = deepcopy(graph)
        bad[key].append(extra)
        assert not runner.assess_control_clock_graph(bad)
    assert not runner.assess_control_clock_graph({})


def test_serial_timesource_role_keeps_exact_five_consumers_and_no_legacy_clock_leak():
    graph=dict(source_publishers=['engine'],relay_publishers=['navigation_control_clock'],
        source_subscribers=['navigation_control_clock','probe'],relay_subscribers=[
            'motion_guard','crawl_controller_ingress','carry_manager','nav_projection','crawl_startup'])
    assert runner.assess_control_clock_graph(graph),'original TimeSource ingress role was not recognized'
    for topic,name in [('relay_subscribers','crawl_controller'),
                       ('relay_subscribers','crawl_controller_ingress'),
                       ('source_subscribers','crawl_controller'),
                       ('source_subscribers','crawl_controller_ingress')]:
        bad=deepcopy(graph);bad[topic].append(name)
        assert not runner.assess_control_clock_graph(bad)


@pytest.mark.parametrize('backend',['waitset','events'])
@pytest.mark.parametrize('bad',['','parent','group','script','thread','node','uid','clock','failed','backend','manifest','type'])
def test_serial_clock_receiver_requires_owned_live_crawl_process_and_thread(tmp_path,bad,backend):
    assert hasattr(runner,'attest_crawl_ingress'),'live receiver/process association missing'
    expected=tmp_path/'install/integrated_robot_navigation/lib/integrated_robot_navigation/crawl_controller'
    expected.parent.mkdir(parents=True);expected.write_text('owned installed entrypoint')
    directory=tmp_path/'proc/11';directory.mkdir(parents=True)
    fields=['S']+['0']*21
    fields[1]=fields[2]='100';fields[19]='123';fields[20]='4096'
    if bad=='parent':fields[1]='99'
    if bad=='group':fields[2]='99'
    (directory/'stat').write_text('11 (owned crawl) '+' '.join(fields))
    executable=expected if bad!='script' else tmp_path/'foreign'
    (directory/'cmdline').write_bytes(b'/usr/bin/python3\0'+str(executable).encode()+b'\0')
    if bad!='thread':(directory/'task/12').mkdir(parents=True)
    dispatch='owned_serial_'+backend
    snapshot=dict(dispatch=dispatch,pid=11,uid=os.getuid(),native_tid=12,
        node_name='crawl_controller_ingress',namespace='/',alive=True,joined=False,error=None,
        clock_subscriptions=['/navigation/control_clock'])
    if backend=='events':snapshot.update(executor_type='EventsExecutor',backend_manifest=runner.event_backend_manifest())
    if bad=='node':snapshot['node_name']='foreign'
    if bad=='uid':snapshot['uid']+=1
    if bad=='clock':snapshot['clock_subscriptions']*=2
    if bad=='failed':snapshot['error']='original receiver failure'
    if bad=='backend':snapshot['dispatch']='owned_serial_events' if backend=='waitset' else 'owned_serial_waitset'
    if bad=='manifest':
        if backend=='events':snapshot['backend_manifest']['extension']['sha256']='0'*64
        else:snapshot['dispatch']='owned_serial_events'
    if bad=='type':
        if backend=='events':snapshot['executor_type']='SingleThreadedExecutor'
        else:snapshot['dispatch']='owned_serial_events'
    if bad:
        with pytest.raises(RuntimeError,match='ingress'):
            runner.attest_crawl_ingress(SimpleNamespace(pid=100),snapshot,expected,proc_root=tmp_path/'proc',expected_dispatch=dispatch)
    else:
        row=runner.attest_crawl_ingress(SimpleNamespace(pid=100),snapshot,expected,proc_root=tmp_path/'proc',expected_dispatch=dispatch)
        assert row['pid']==11 and row['start_ticks']==123 and row['native_tid']==12
        assert row['entrypoint_sha256']==runner.file_digest(expected)


@pytest.mark.parametrize('bad', ['', 'parent', 'group', 'exe', 'library', 'inode', 'hash'])
def test_relay_attestation_requires_same_owned_executable_and_mapped_library(tmp_path, bad):
    assert hasattr(runner, 'attest_control_clock'), 'actual relay executable/library binding missing'
    directory = tmp_path/'proc/11'
    directory.mkdir(parents=True)
    executable, library = tmp_path/'control_clock_relay', tmp_path/'libnavigation_control_clock.so'
    executable.write_bytes(b'executable-fixture-not-run')
    library.write_bytes(b'library-fixture-not-loaded')
    (directory/'exe').symlink_to(executable)
    fields = ['S', '100', '100', '50', '0', '-1', '0', '7', '0', '2', '0',
              '40', '10', '0', '0', '20', '0', '3', '0', '123', '4096', '8']
    if bad == 'parent': fields[1] = '99'
    if bad == 'group': fields[2] = '99'
    (directory/'stat').write_text('11 (owned clock) '+' '.join(fields))
    stat = library.stat()
    device = f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}'
    inode = stat.st_ino+1 if bad == 'inode' else stat.st_ino
    (directory/'maps').write_text('' if bad == 'library' else f'000-fff r-xp 0000 {device} {inode} {library}\n')
    expected = dict(control_clock_path=str(executable), control_clock_sha256=runner.file_digest(executable),
                    control_clock_library=str(library), control_clock_library_sha256=runner.file_digest(library))
    if bad == 'exe': expected['control_clock_path'] = str(tmp_path/'foreign')
    if bad == 'hash': expected['control_clock_library_sha256'] = '0'*64
    if bad:
        with pytest.raises(RuntimeError, match='clock'):
            runner.attest_control_clock(SimpleNamespace(pid=100), 11, expected, proc_root=tmp_path/'proc')
    else:
        row = runner.attest_control_clock(SimpleNamespace(pid=100), 11, expected, proc_root=tmp_path/'proc')
        assert row['pid'] == 11 and row['start_ticks'] == 123
        assert row['sha256'] == runner.file_digest(executable)
