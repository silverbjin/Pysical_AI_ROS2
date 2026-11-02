"""Breaks caught: wrong leg ordering, duplicate links or disconnected model."""
import importlib
from pathlib import Path

import pytest
import xacro


def model_api():
    assert importlib.util.find_spec('integrated_robot_navigation.model'), 'model compiler missing'
    return importlib.import_module('integrated_robot_navigation.model')


@pytest.fixture
def urdf():
    path = Path(__file__).resolve().parents[2] / 'integrated_robot_description/urdf/robot_system.urdf.xacro'
    return xacro.process_file(str(path)).toxml()


def test_named_actual_robot_contract(urdf):
    model = model_api().compile_model(urdf)
    assert model.feet == ('fr_foot', 'fl_foot', 'rr_foot', 'rl_foot')
    assert model.joint_names[:3] == ('fr_hip_joint', 'fr_thigh_joint', 'fr_calf_joint')
    assert len(model.joint_names) == 12
    assert model.limits['fr_hip_joint'] == (-.8, .8, 10., 20.)
    assert model.masses['base_link'][0] == 6.
    assert model.chains['fr_foot'].joint_names == (
        'fr_hip_joint', 'fr_thigh_joint', 'fr_calf_joint')


@pytest.mark.parametrize('old,new', [
    ('name="fr_foot"', 'name="fl_foot"'),
    ('parent link="fr_calf_link"', 'parent link="nonexistent"'),
])
def test_epoch_and_names_reject_invalid_model(urdf, old, new):
    with pytest.raises(ValueError):
        model_api().compile_model(urdf.replace(old, new))
