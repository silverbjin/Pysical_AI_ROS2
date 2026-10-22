"""Breaks caught: granting motion from a candidate, stale hashes or a ready flag."""
from dataclasses import replace
import importlib

import pytest


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.carry_profile'), 'carry profile missing'
    return importlib.import_module('integrated_robot_navigation.carry_profile')


def test_offline_candidate_cannot_enable_either_engine(nav_robot_model):
    robot_model = nav_robot_model
    p = api().prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))
    assert p.state == 'offline'
    assert p.model_sha256 == robot_model.model_sha256
    for engine in ('mujoco', 'gazebo'):
        assert api().validate_profile(p, robot_model, engine) == (False, 'native_validation_required')


def test_changed_model_hash_rejects_old_profile(nav_robot_model):
    robot_model = nav_robot_model
    p = api().prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))
    assert api().validate_profile(replace(p, model_sha256='0'*64), robot_model,
                                  'mujoco') == (False, 'model_hash')


def test_handwritten_validated_flag_is_insufficient(nav_robot_model):
    robot_model = nav_robot_model
    p = api().prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))
    assert not api().validate_profile(replace(p, state='native_validated'), robot_model, 'mujoco')[0]


@pytest.mark.parametrize('q', [(0., 1.2, -3., 0., .8, 0.),
                              (0., 1.2, float('nan'), 0., .8, 0.)])
def test_invalid_carry_angles_are_rejected(robot_model, q):
    with pytest.raises(ValueError):
        api().prepare_profile(robot_model, q)


def test_collision_model_is_checked_not_only_joint_limits(nav_robot_model):
    from integrated_robot_navigation.model import compile_model
    robot_model = nav_robot_model
    enlarged = compile_model(robot_model.urdf.replace(
        'size="0.60 0.30 0.15"', 'size="0.60 0.30 3.0"'))
    with pytest.raises(ValueError, match='collision|ground'):
        api().prepare_profile(enlarged, (0., 1.2, -2., 0., .8, 0.))


def test_legacy_body_thigh_overlap_is_not_silently_ignored(robot_model):
    with pytest.raises(ValueError, match='collision'):
        api().prepare_profile(robot_model, (0., 1.2, -2., 0., .8, 0.))


@pytest.mark.parametrize('key,value', [
    ('footprint_margin_m', .049), ('sensor_max_age_s', .201),
    ('max_roll_pitch', .16), ('max_vx', .011),
])
def test_preparation_cannot_weaken_safety_contract(nav_robot_model, key, value):
    module = api()
    limits = module.default_limits()
    limits[key] = value
    with pytest.raises(ValueError, match='limits'):
        module.prepare_profile(nav_robot_model, (0., 1.2, -2., 0., .8, 0.), limits=limits)
