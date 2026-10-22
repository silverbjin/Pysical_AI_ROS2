"""Capture identity, clock-domain and evidence gates; no synthetic native PASS."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from latency_trace_13_4 import TraceCollector, analyze_trace
from integrated_robot_vision.trace import KEYS, decode_record

RUN = '424240ff-0bfe-4a4b-92d4-93f6a78d49b8'
BOOT = '11111111-1111-4111-8111-111111111111'


def record(stage, *, capture=1_000_000_000, epoch=0, sequence=1):
    times = {
        'camera': [10, 20, 30, 40, 100, 200, 210, 220, 230, 240, 250, 260, 270],
        'detector': [280, 290, 300, 310, 320, 330, 340, 350, 360],
        'fusion': [282, 283, 370, 380, 390, 400, 410, 420, 430, 440, 450],
        'tracking': [460, 470, 480],
    }
    keys = KEYS[stage] if stage != 'tracking' else ('target_receive', 'decision', 'dispatch')
    index = tuple(KEYS).index(stage)+1
    return dict(schema_version=1, run_id=RUN,
        producer_id=f'00000000-0000-4000-8000-{index:012d}', pid=index, tid=index,
        clock_id='linux/CLOCK_MONOTONIC', boot_id=BOOT, stage=stage,
        event_sequence=sequence, source_frame='camera_optical_frame', capture_ns=capture,
        local_epoch=epoch, native_sequence=sequence if stage == 'camera' else None,
        times_ns=dict(zip(keys, times[stage])),
        outcome='DISPATCH' if stage == 'tracking' else 'PUBLISHED', ros_now_ns=1_100_000_000)


def rows():
    # Local epochs intentionally differ; they are NOT a shared generation.
    return [dict(received_ns=1000+i, record=record(stage, epoch=i*7))
            for i, stage in enumerate(KEYS)]


def test_reordered_delivery_uses_producer_times():
    value = rows()
    result = analyze_trace(value, expected_run_id=RUN, require_native=True)
    assert result['segments']['native_render']['p50_ns'] == 100
    assert result['segments']['native_to_dispatch']['max_ns'] == 470
    reversed_rows = list(reversed(deepcopy(value)))
    for row in reversed_rows:
        row['received_ns'] += 100_000
    reverse = analyze_trace(reversed_rows, expected_run_id=RUN, require_native=True)
    assert reverse['segments'] == result['segments']
    assert result['counts']['dropped'] is None  # no publisher totals were proved


def test_ambiguous_capture_never_produces_latency():
    value = rows()
    other = deepcopy(value[0])
    other['record']['local_epoch'] += 1
    other['record']['native_sequence'] += 1
    other['record']['event_sequence'] += 1
    value.append(other)
    result = analyze_trace(value, expected_run_id=RUN, require_native=True)
    assert result['counts']['ambiguous'] > 0
    assert result['segments'] == {}
    assert result['analysis_status'] != 'PASS'


def test_conflicting_event_never_chooses_the_first_arrival():
    value = rows()
    conflict = deepcopy(value[0])
    conflict['record']['local_epoch'] += 1
    value.append(conflict)  # same producer/event ID, different snapshot epoch
    result = analyze_trace(value, expected_run_id=RUN, require_native=True)
    assert 'native_to_dispatch' not in result['segments']
    assert result['counts']['ambiguous'] > 0


@pytest.mark.parametrize('damage', ['boot', 'clock', 'negative', 'run', 'missing', 'limit'])
def test_broken_links_are_not_filled_with_latest_or_observer_time(damage):
    value = rows()
    if damage == 'boot':
        value[1]['record']['boot_id'] = str(uuid4())
    elif damage == 'clock':
        value[1]['record']['clock_id'] = 'ros/now'
    elif damage == 'negative':
        value[0]['record']['times_ns']['render_end'] = 99
    elif damage == 'run':
        value[1]['record']['run_id'] = str(uuid4())
    elif damage == 'missing':
        value.pop(1)
    else:
        value[1]['record']['event_sequence'] = 20001
    result = analyze_trace(value, expected_run_id=RUN, require_native=True)
    assert result['analysis_status'] != 'PASS'
    assert 'native_to_dispatch' not in result['segments']
    assert result['errors'] or result['missing_stages'] or result['counts']['unmatched']


@pytest.mark.parametrize('damage', ['native_partial', 'fusion_before_tf', 'fusion_before_receive'])
def test_incomplete_publication_or_impossible_fusion_causality_never_joins(damage):
    value = rows()
    if damage == 'native_partial':
        value[0]['record']['outcome'] = 'EPOCH_INVALIDATED'
    elif damage == 'fusion_before_tf':
        value[2]['record']['times_ns']['tf_end'] = 600
    else:
        value[2]['record']['times_ns']['rgb_receive'] = 600
    result = analyze_trace(value, expected_run_id=RUN, require_native=True)
    assert 'native_to_dispatch' not in result['segments']
    assert result['counts']['malformed'] or result['counts']['unmatched']


def test_null_target_and_gate_loss_ages_stay_in_their_own_clock_domains():
    lost = record('tracking')
    lost['outcome'] = 'GATE_LOST'
    lost['times_ns'] = dict(target_receive=100, decision=200, gate_lost=400_000_100)
    lost['ros_now_ns'] = 1_350_000_000
    absent = deepcopy(lost)
    absent.update(capture_ns=None, source_frame='', event_sequence=2)
    absent['times_ns'] = {'decision': 500_000_000}
    absent['outcome'] = 'NO_COMMAND'
    result = analyze_trace([dict(received_ns=999_000_000, record=v) for v in (lost, absent)],
                           expected_run_id=RUN, require_native=False)
    assert result['gate_losses'][0]['ros_age_ns'] == 350_000_000
    assert result['gate_losses'][0]['receipt_age_ns'] == 400_000_000
    assert result['counts']['no_target'] == 1


def test_gate_loss_without_source_retains_unknown_age_not_fake_zero():
    value = record('tracking', capture=None)
    value.update(source_frame='', outcome='GATE_LOST')
    value['times_ns'] = dict(decision=100, gate_lost=200)
    result = analyze_trace([dict(received_ns=1000, record=value)],
                           expected_run_id=RUN, require_native=False)
    assert len(result['gate_losses']) == 1
    assert result['gate_losses'][0]['ros_age_ns'] is None
    assert result['gate_losses'][0]['receipt_age_ns'] is None


def test_partial_trace_cannot_promote_native_failure(tmp_path):
    from verify_vision_13_4 import EvidenceRun
    summary = analyze_trace(rows(), expected_run_id=RUN, require_native=True)
    with EvidenceRun(tmp_path/'native-fail', {'native', 'terminal', 'clean_shutdown'}) as run:
        run.result['trace_summary'] = summary
        with pytest.raises(RuntimeError):
            run.finish(dict(native=False, terminal=False, clean_shutdown=False))
    assert run.result['status'] == 'FAIL'
    assert run.result['checks']['clean_shutdown'] is False


def test_native_trace_requires_the_audited_live_pid_and_boot():
    import run_vision_13_4 as runner
    value = rows()
    proof = dict(egl_renderer=['unit contract, not a native run'], library_sha256='a'*64,
                 mailbox_library_sha256='b'*64, native_pid=1, boot_id=BOOT)
    assert runner.native_trace_origin_verified(value, proof)
    wrong = deepcopy(value)
    wrong[0]['record']['pid'] = 999
    assert not runner.native_trace_origin_verified(wrong, proof)
    wrong[0]['record']['pid'] = 1
    wrong[0]['record']['boot_id'] = str(uuid4())
    assert not runner.native_trace_origin_verified(wrong, proof)
    assert not runner.native_trace_origin_verified(value[1:], proof)
    assert not runner.native_trace_origin_verified(value, {})


def test_collector_caps_records_and_producer_metadata_without_stopping_ingress():
    collector = TraceCollector(RUN)
    assert collector.MAX_PER_PRODUCER == 20000 and collector.MAX_TOTAL == 80000
    assert collector.MAX_PRODUCERS == 16
    value = record('tracking')
    payload = json.dumps(value)
    for _ in range(20000):
        assert collector.add(payload, received_ns=1000)
    assert not collector.add(payload, received_ns=1001)
    assert len(collector.records) == 20000 and collector.counts['dropped'] == 1
    for index in range(16):
        value['producer_id'] = str(uuid4())
        collector.add(json.dumps(value), received_ns=1002+index)
    assert len(collector.producers) == 16
    assert collector.counts['dropped'] == 2
    assert not collector.add('bad JSON', received_ns=1003)
    assert collector.counts['malformed'] == 1
    assert len(collector.records) == 20015


def test_collector_total_limit_and_exact_serialized_rows(tmp_path):
    collector = TraceCollector(RUN)
    for index in range(4):
        value = record('tracking')
        value['producer_id'] = str(uuid4())
        payload = json.dumps(value)
        for _ in range(20000):
            assert collector.add(payload, received_ns=500)
    value['producer_id'] = str(uuid4())
    assert not collector.add(json.dumps(value), received_ns=501)
    assert len(collector.records) == 80000
    # Only a tiny actual capture set is written here; no test fixture is native evidence.
    small = TraceCollector(RUN)
    assert small.add(json.dumps(record('camera')), received_ns=999)
    small.save(tmp_path, require_native=True)
    row = json.loads((tmp_path/'trace.jsonl').read_text())
    assert set(row) == {'received_ns', 'record'} and row['received_ns'] == 999
    assert (tmp_path/'trace_summary.json').is_file()


def test_cpp_real_ros_trace_is_decoded_by_python():
    import os
    import hashlib
    from ament_index_python.packages import get_package_prefix
    build = os.environ.get('CH13_EGL_BUILD')
    selected = os.environ.get('CH13_CAMERA_TEST_BINARY')
    if selected:
        executable = Path(selected)
    elif build:
        executable = Path(build)/'integrated_robot_camera/test_camera_trace'
    else:
        # Only the matching active installation, never a newest-build glob.
        install = Path(get_package_prefix('integrated_robot_camera')).parent
        assert install.name.startswith('install'), 'custom layout requires CH13_CAMERA_TEST_BINARY'
        executable = install.parent/install.name.replace('install', 'build', 1)/(
            'integrated_robot_camera/test_camera_trace')
    source = Path(__file__).resolve().parents[1]/'ros2_ws/src/integrated_robot_camera'
    manifest = json.loads((executable.parent/'source_manifest.json').read_text())
    assert manifest['test/test_camera_trace.cpp'] == hashlib.sha256(
        (source/'test/test_camera_trace.cpp').read_bytes()).hexdigest(), 'stale selected test build'
    result = subprocess.run([str(executable),
        '--gtest_filter=TraceTest.TraceEscapesStringsAndCapsUtf8Bytes', '--gtest_output='],
        capture_output=True, text=True, timeout=20.)
    assert result.returncode == 0, result.stdout+result.stderr
    payloads = [line.removeprefix('CAMERA_TRACE_CONTRACT ') for line in result.stdout.splitlines()
                if line.startswith('CAMERA_TRACE_CONTRACT ')]
    assert len(payloads) == 1, 'C++ actual ROS publisher/subscriber contract record missing'
    value = decode_record(payloads[0])
    assert value['stage'] == 'camera' and value['native_sequence'] == 7
    assert value['source_frame'] == 'cam"\\\n한글'


def test_actual_observer_subscriptions_are_opt_in_and_preserve_receipt(tmp_path):
    import rclpy
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import qos_profile_sensor_data
    from std_msgs.msg import String
    import time
    from vision_observer_13_4 import VisionObserver
    rclpy.init(domain_id=150)
    observer, peer, executor = None, None, SingleThreadedExecutor()
    try:
        observer = VisionObserver(tmp_path)
        assert observer.trace_subscriptions == [] and observer.trace_collector is None
        observer.destroy_node()
        observer = VisionObserver(tmp_path, trace_enabled=True, trace_run_id=RUN)
        peer = Node('trace_routing_peer')
        executor.add_node(observer)
        executor.add_node(peer)
        assert len(observer.trace_subscriptions) == 4
        for sub in observer.trace_subscriptions:
            assert sub.qos_profile.depth == 32
        topics = {'camera': '/vision/camera_trace', 'detector': '/vision/detector_trace',
                  'fusion': '/vision/fusion_trace', 'tracking': '/architecture/tracking_trace'}
        pubs = {stage: peer.create_publisher(String, topic, qos_profile_sensor_data)
                for stage, topic in topics.items()}
        start = time.monotonic_ns()
        for stage, pub in pubs.items():
            pub.publish(String(data=json.dumps(record(stage))))
        end = time.monotonic()+1.
        while len(observer.trace_collector.records) < 4 and time.monotonic() < end:
            executor.spin_once(timeout_sec=.005)
        assert len(observer.trace_collector.records) == 4
        assert all(v['received_ns'] >= start for v in observer.trace_collector.records)
        assert observer.count_publishers('/arm_trajectory_controller/joint_trajectory') == 0
    finally:
        executor.shutdown(timeout_sec=2.)
        if observer is not None:
            observer.destroy_node()
        if peer is not None:
            peer.destroy_node()
        rclpy.try_shutdown()
