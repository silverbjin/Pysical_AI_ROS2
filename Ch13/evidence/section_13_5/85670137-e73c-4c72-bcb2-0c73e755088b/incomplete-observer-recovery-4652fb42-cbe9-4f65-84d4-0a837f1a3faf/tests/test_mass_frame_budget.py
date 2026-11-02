"""Break: repeated shared-prefix FK consumes sensor freshness during SHIFT."""
from collections import Counter
from dataclasses import replace

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


class CountedInertialPoint(tuple):
    def __new__(cls,values):
        value=super().__new__(cls,values);value.materializations=0;return value

    def __iter__(self):
        self.materializations+=1
        return super().__iter__()


def test_immutable_mass_geometry_is_compiled_once_while_measurements_remain_fresh(nav_robot_model):
    point=CountedInertialPoint((.0123456789,0.,0.))
    model=replace(nav_robot_model,masses={'base_link':(1.,point),
        'fr_thigh_link':(3.,(0.,0.,-.12))})
    q={name:0. for name in model.limits}
    first=center_of_mass(model,q,np.eye(4))
    q['fr_thigh_joint']=.5
    second=center_of_mass(model,q,np.eye(4))
    assert np.linalg.norm(np.asarray(first)-second)>.001
    assert point.materializations<=1, 'unchanging inertial geometry was rebuilt for another sensor capture'
