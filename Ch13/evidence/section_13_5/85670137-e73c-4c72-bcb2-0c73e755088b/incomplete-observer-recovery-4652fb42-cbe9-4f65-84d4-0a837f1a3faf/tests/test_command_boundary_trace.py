"""Actual DDS publication provenance; not a native locomotion verdict."""
import json
import time
from std_srvs.srv import Trigger
from test_crawl_lifecycle import crawl_rig
from test_crawl_safety_ros import activate


def test_report_keeps_original_decision_and_publication_times(crawl_rig):
    rig = crawl_rig
    activate(rig)
    client = rig.node.create_client(Trigger, '/crawl_controller/report')
    assert client.wait_for_service(timeout_sec=1.)
    future = client.call_async(Trigger.Request())
    until = time.monotonic()+2.
    while not future.done() and time.monotonic() < until:
        rig.pump(.02)
    assert future.done() and future.result().success
    report = json.loads(future.result().message)
    assert 'command_publications' in report, 'no publication -> CM -> physical application provenance'
    trace = report['command_publications']
    assert trace['capacity'] == 512
    assert trace['rows'] and trace['total'] >= len(trace['rows'])
    assert trace['joint_names'] == list(rig.guard.model.joint_names)
    previous = -1
    wire_values = [list(m.data) for m in rig.commands]
    for row in trace['rows']:
        assert previous < row['sequence']
        previous = row['sequence']
        assert row['decision_wall_ns'] <= row['publish_started_ns'] <= row['publish_finished_ns']
        assert row['decision_ros_ns'] > 0
        assert row['generation'] == report['generation']
        assert row['values'] in wire_values
    count = rig.guard.command_publication_count
    rig.pump(.28, clock=False)
    assert rig.crawl_states[-1].state == 'FAULT'
    after_fault = rig.guard.command_publication_count
    rig.pump(.08, clock=False)
    assert rig.guard.command_publication_count == after_fault >= count
