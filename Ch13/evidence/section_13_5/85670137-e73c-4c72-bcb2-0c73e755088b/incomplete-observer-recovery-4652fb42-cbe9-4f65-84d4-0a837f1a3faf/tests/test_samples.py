"""Breaks caught: refreshing duplicate age, accepting invalid or old sessions."""
from dataclasses import replace
import importlib

import pytest


def sample_api():
    spec = importlib.util.find_spec('integrated_robot_navigation.samples')
    assert spec is not None, 'navigation sample implementation is missing'
    return importlib.import_module('integrated_robot_navigation.samples')


def test_duplicate_does_not_refresh_receipt():
    api = sample_api()
    cache = api.ReceiptCache(epoch=4)
    first = api.Sample(1_000_000_000, 10_000_000_000, 4, 1, 'odom', (1., 2., 3.))
    assert cache.receive('body', first) == first
    replay = replace(first, received_ns=11_000_000_000)
    assert cache.receive('body', replay).received_ns == 10_000_000_000
    assert api.sample_valid(cache.get('body'), 1_000_000_000, 11_000_000_000, 4,
                            max_age_ns=200_000_000) == (False, 'wall_age')


@pytest.mark.parametrize('changes,reason', [
    ({'epoch': 3}, 'epoch'), ({'stamp_ns': 1_000_000_001}, 'ros_age'),
    ({'received_ns': 10_000_000_001}, 'wall_age'),
    ({'data': (float('nan'),)}, 'nonfinite'),
    ({'data': (float('inf'),)}, 'nonfinite'), ({'frame_id': ''}, 'frame'),
])
def test_reject_invalid_samples(changes, reason):
    api = sample_api()
    sample = api.Sample(1_000_000_000, 10_000_000_000, 4, 1, 'odom', (1.,))
    assert api.sample_valid(replace(sample, **changes), 1_000_000_000,
                            10_000_000_000, 4, max_age_ns=200_000_000) == (False, reason)


def test_age_boundary_and_missing_bundle():
    api = sample_api()
    sample = api.Sample(1_000_000_000, 10_000_000_000, 4, 1, 'odom', (1.,))
    assert api.sample_valid(sample, 1_200_000_000, 10_200_000_000, 4,
                            max_age_ns=200_000_000) == (True, '')
    assert api.sample_valid(sample, 1_200_000_001, 10_200_000_000, 4,
                            max_age_ns=200_000_000) == (False, 'ros_age')
    bundle = api.SensorBundle(sample, sample, sample, sample, sample, sample)
    assert api.validate_bundle(bundle, 1_000_000_000, 10_000_000_000, 4) == (True, '')
    assert api.validate_bundle(replace(bundle, imu=None), 1_000_000_000,
                               10_000_000_000, 4) == (False, 'imu:missing')


def test_epoch_reset_and_out_of_order_never_replace_newer():
    api = sample_api()
    cache = api.ReceiptCache(epoch=4)
    first = api.Sample(1_000_000_000, 10_000_000_000, 4, 2, 'odom', (1.,))
    cache.receive('body', first)
    with pytest.raises(ValueError, match='order'):
        cache.receive('body', replace(first, stamp_ns=900_000_000, sequence=1))
    cache.reset(5)
    assert cache.get('body') is None
    with pytest.raises(ValueError, match='epoch'):
        cache.receive('body', first)
    with pytest.raises(ValueError, match='epoch'):
        cache.reset(4)
