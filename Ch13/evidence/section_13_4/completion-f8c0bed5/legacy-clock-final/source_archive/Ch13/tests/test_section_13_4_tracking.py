"""Identity-aware filters must not refresh or average a lost object's state."""
import math

import numpy as np
import pytest

from integrated_robot_vision.contracts import Box2D, Observation
from integrated_robot_vision.tracker import TrackManager, TargetFilter


def observation(stamp=1., x=0., *, cls='cup', epoch=0, cal='a', frame='odom',
                cx=50., score=.9):
    return Observation(stamp, epoch, cal, frame, Box2D(cx, 50., 20., 20., cls, score),
                       np.array([x, 0., 1.]), np.eye(3)*1e-6)


def test_variable_dt_and_fixed_alpha_filters():
    filt = TargetFilter(tau=.2)
    np.testing.assert_allclose(filt.update(np.zeros(3), 1.), [0, 0, 0])
    assert filt.update(np.array([.1, 0, 0]), 1.2)[0] == pytest.approx(.1*(1-math.exp(-1)))
    fixed = TargetFilter(alpha=.25)
    fixed.update(np.zeros(3), 1.)
    assert fixed.update(np.array([.1, 0, 0]), 1.2)[0] == pytest.approx(.025)
    with pytest.raises(ValueError):
        fixed.update(np.zeros(3), 1.2)


@pytest.mark.parametrize('kwargs', [dict(tau=0), dict(tau=math.nan), dict(alpha=0),
                                    dict(alpha=1.01), dict(alpha=math.nan)])
def test_filter_rejects_undefined_parameters(kwargs):
    with pytest.raises(ValueError):
        TargetFilter(**kwargs)


@pytest.mark.parametrize('changes', [dict(cls='bottle'), dict(epoch=1), dict(cal='b')])
def test_new_track_never_averages_old_object(changes):
    manager = TrackManager(instance_id='fixed')
    first = manager.update([observation()], 1., 10.)
    second = manager.update([observation(1.1, .1, **changes)], 1.1, 10.1)
    assert second.valid
    assert first.track_id != second.track_id
    assert second.point[0] == .1


def test_non_odom_input_resets_without_relabeling_map_coordinates():
    manager = TrackManager(instance_id='fixed')
    first = manager.update([observation()], 1., 10.)
    rejected = manager.update([observation(1.1, .1, frame='map')], 1.1, 10.1)
    assert not rejected.valid
    assert rejected.stamp == 1.
    fresh = manager.update([observation(1.2, .1)], 1.2, 10.2)
    assert fresh.track_id != first.track_id
    assert fresh.point[0] == .1


def test_outlier_and_duplicate_do_not_extend_ttl_and_reappearance_is_new_id():
    manager = TrackManager(instance_id='fixed')
    first = manager.update([observation()], 1., 10.)
    rejected = manager.update([observation(1.2, .21)], 1.2, 10.2)
    assert not rejected.valid and rejected.stamp == 1.
    duplicate = manager.update([observation(1., .1)], 1.25, 10.25)
    assert not duplicate.valid and duplicate.stamp == 1.
    expired = manager.expire(1.301, 10.301)
    assert expired is not None and not expired.valid and expired.status == 'LOST'
    assert expired.stamp == 1.
    fresh = manager.update([observation(1.31, .21)], 1.31, 10.31)
    assert fresh.valid and fresh.track_id != first.track_id
    assert fresh.point[0] == .21


def test_ambiguous_association_and_empty_detection_do_not_publish_a_new_point():
    manager = TrackManager(instance_id='fixed')
    assert manager.update([], 1., 10.) is None
    assert manager.update([observation(score=.9), observation(x=.05, score=.88)], 1., 10.) is None
    first = manager.update([observation()], 1.01, 10.01)
    ambiguous = manager.update([observation(1.1, .03, cx=50),
                                 observation(1.1, .04, cx=50.1)], 1.1, 10.1)
    assert not ambiguous.valid and ambiguous.stamp == first.stamp
    empty = manager.update([], 1.15, 10.15)
    assert not empty.valid and empty.stamp == first.stamp
    assert manager.expire(1.31, 10.31).status == 'LOST'


def test_ros_clock_pause_and_backward_reset_cannot_revive_old_identity():
    manager = TrackManager(instance_id='fixed')
    first = manager.update([observation()], 1., 10.)
    assert manager.expire(1., 10.301).status == 'LOST'
    manager.reset('RESET', epoch=1)
    fresh = manager.update([observation(.5, .1, epoch=1)], .5, 10.4)
    assert fresh.valid and fresh.track_id != first.track_id
    assert fresh.point[0] == .1


def test_innovation_and_iou_gates_reject_far_or_nonoverlapping_candidates():
    manager = TrackManager(instance_id='fixed')
    first = manager.update([observation()], 1., 10.)
    miss = manager.update([observation(1.1, .05, cx=90)], 1.1, 10.1)
    assert not miss.valid and miss.stamp == first.stamp
    assert manager.observation.stamp == 1.
