"""Shared decoder/inbox: future clocks, duplicate receipt and local clear."""
import importlib
from dataclasses import replace

from sensor_msgs.msg import LaserScan
from integrated_robot_navigation.samples import Sample


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.observations'), 'shared receiver missing'
    return importlib.import_module('integrated_robot_navigation.observations')


def test_future_capture_waits_without_renewing_first_receipt():
    inbox = api().SensorInbox(0)
    sample = Sample(2_000_000_000, 10_000_000_000, 0, 1, 'odom', (1.,))
    inbox.receive('body', sample)
    inbox.receive('body', replace(sample, received_ns=11_000_000_000))
    assert inbox.bundle(1_999_999_999).body is None
    assert inbox.bundle(2_000_000_000).body.received_ns == 10_000_000_000


def test_clear_rejects_pre_reset_capture_even_if_delivered_late():
    inbox = api().SensorInbox(0)
    inbox.clear(2_000_000_000)
    inbox.receive('body', Sample(2_000_000_000, 11_000_000_000, 0, 1, 'odom', (1.,)))
    assert inbox.bundle(2_000_000_000).body is None


def test_scan_no_hit_is_explicit_not_zero_or_infinite_canonical_data():
    message = LaserScan(range_min=.05, range_max=10., ranges=[float('inf'), .5])
    message.header.stamp.sec, message.header.frame_id = 4, 'lidar_link'
    sample = api().sensor_sample('scan', message, 10_000_000_000, 0)
    assert sample.stamp_ns == 4_000_000_000 and sample.received_ns == 10_000_000_000
    assert sample.data['ranges'] == (10., .5) and sample.data['hits'] == (False, True)
