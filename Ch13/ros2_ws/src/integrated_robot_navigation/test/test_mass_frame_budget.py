"""Break: repeated shared-prefix FK consumes sensor freshness during SHIFT."""
from collections import Counter

import numpy as np
import pytest

from integrated_robot_navigation.support import center_of_mass


class CountedPositions(dict):
    def __init__(self, values):
        super().__init__(values)
        self.reads = Counter()

    def __getitem__(self, key):
        self.reads[key] += 1
        return super().__getitem__(key)


def test_one_com_query_evaluates_each_shared_joint_position_only_once(nav_robot_model):
    q = CountedPositions({name: 0. for name in nav_robot_model.limits})
    center_of_mass(nav_robot_model, q, np.eye(4))
    assert set(q.reads) == set(nav_robot_model.limits)
    assert max(q.reads.values()) == 1, q.reads


def test_pose_cache_never_reuses_a_previous_measurement(nav_robot_model):
    q = {name: 0. for name in nav_robot_model.limits}
    first = center_of_mass(nav_robot_model, q, np.eye(4))
    q['arm_joint_2'] = .5
    changed = center_of_mass(nav_robot_model, q, np.eye(4))
    assert np.linalg.norm(np.asarray(changed)-first) > .001
    q['arm_joint_2'] = 0.
    assert center_of_mass(nav_robot_model, q, np.eye(4)) == pytest.approx(first, abs=1e-12)
