"""Actual DDS sensor fault/report; this fixture is not physical G1 evidence."""
from dataclasses import replace
import json
import time

from lifecycle_msgs.msg import Transition
from std_srvs.srv import Trigger
import test_motion_guard_ros
from test_crawl_lifecycle import crawl_rig


def test_report_exposes_live_phase_and_preload_targets_before_any_fault(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.08)
    client = rig.node.create_client(Trigger, '/crawl_controller/report')
    assert client.wait_for_service(timeout_sec=1.)
    future = client.call_async(Trigger.Request())
    deadline = time.monotonic()+1.
    while not future.done() and time.monotonic() < deadline:
        rig.pump(.02)
    assert future.done() and future.result().success
    report = json.loads(future.result().message)
    current = report['current']
    assert report['first_fault'] is None and report['first_stop'] is None
    assert current['state'] == 'STAND' and current['phase'] == 'STAND'
    assert set(current['targets']) == set(rig.model.feet)
    assert all(len(point) == 3 for point in current['targets'].values())
    assert current['phase_start_ns'] > 0 and current['plan_pending'] is False
    assert current['unload_start_ns'] is None


def test_first_fault_reports_selected_capture_and_is_not_overwritten(crawl_rig, monkeypatch):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.1)
    original = test_motion_guard_ros.bundle

    def unsupported(model):
        value = original(model)
        return replace(value, contacts=replace(value.contacts,
            data={**value.contacts.data, 'forces': (0., 30., 0., 30.),
                  'touching': (False, True, False, True)}))

    monkeypatch.setattr(test_motion_guard_ros, 'bundle', unsupported)
    rig.pump(.12)
    assert rig.crawl_states[-1].fault_reason == 'current measured support lost'
    client = rig.node.create_client(Trigger, '/crawl_controller/report')
    assert client.wait_for_service(timeout_sec=1.), 'selected fault snapshot service missing'

    def report():
        future = client.call_async(Trigger.Request())
        deadline = time.monotonic()+1.
        while not future.done() and time.monotonic() < deadline:
            rig.pump(.02)
        assert future.done() and future.result().success
        return json.loads(future.result().message)['first_fault']

    snapshot = report()
    assert snapshot['reason'] == 'current measured support lost'
    assert snapshot['scope'] == 'first_tick_observing_fault'
    assert snapshot['transition_during_advance'] is True
    assert snapshot['samples']['contacts']['data']['forces'] == [0., 30., 0., 30.]
    assert snapshot['samples']['contacts']['stamp_ns'] <= snapshot['ros_ns']
    assert snapshot['model_sha256'] == rig.model.model_sha256
    count = len(rig.commands)
    monkeypatch.setattr(test_motion_guard_ros, 'bundle', original)
    rig.pump(.1)
    assert report() == snapshot, 'healthy later data must not rewrite the failure input'
    assert len(rig.commands) == count and not rig.crawl_states[-1].ready


def test_guard_age_stop_records_selected_header_receipt_and_clock_not_kernel_fault(crawl_rig):
    rig = crawl_rig
    assert rig.transition(Transition.TRANSITION_CONFIGURE)
    assert rig.transition(Transition.TRANSITION_ACTIVATE)
    rig.pump(.08)
    rig.gate_delay_ns = 250_000_000
    # A reordered old packet cannot replace the last valid capture. Wait for
    # that capture's unchanged200ms validity to expire, not an arbitrary120ms.
    deadline = time.monotonic()+.5
    while not rig.crawl_states[-1].fault_reason and time.monotonic() < deadline:
        rig.pump(.02)
    assert rig.crawl_states[-1].fault_reason == 'guard:ros_age'
    client = rig.node.create_client(Trigger, '/crawl_controller/report')
    assert client.wait_for_service(timeout_sec=1.)

    def report():
        future = client.call_async(Trigger.Request())
        deadline = time.monotonic()+1.
        while not future.done() and time.monotonic() < deadline:
            rig.pump(.02)
        assert future.done() and future.result().success
        return json.loads(future.result().message)

    result = report()
    snapshot = result['first_stop']
    assert snapshot['reason'] == 'guard:ros_age'
    assert snapshot['ros_ns']-snapshot['guard']['stamp_ns'] > 200_000_000
    assert snapshot['guard']['received_ns'] <= snapshot['wall_ns']
    assert snapshot['guard_receipts'] and snapshot['tick_spans']
    assert result['first_fault'] is None, 'STOPPING is not a kernel FAULT'
    rig.gate_delay_ns = 0
    rig.pump(.1)
    assert report()['first_stop'] == snapshot, 'later fresh status cannot rewrite first stop input'
