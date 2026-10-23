"""Command continuity under encoder load error; arithmetic, not native proof."""
from dataclasses import replace
import xml.etree.ElementTree as ET

import pytest

from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.gait import CrawlMachine
from guard_fixture import bundle


def test_activation_preserves_held_spring_preload_not_loaded_encoder_zero_error(nav_robot_model):
    model = nav_robot_model
    state = bundle(model)
    held = {name: state.joints.data['position'][name] for name in model.joint_names}
    q = dict(state.joints.data['position'])
    q['fr_calf_joint'] = 1.035  # loaded encoder, prior command is still1.000
    state = replace(state, joints=replace(state.joints,
        data=dict(position=q, velocity=state.joints.data['velocity'])))
    machine = CrawlMachine(model, default_limits())
    machine.reset(state, state.body.stamp_ns, state.body.received_ns, held_targets=held)
    result = machine.advance(state, (0., 0., 0.), state.body.stamp_ns, state.body.received_ns)
    assert result.state == 'STAND', result.reason
    assert result.joint_targets['fr_calf_joint'] == pytest.approx(1., abs=1e-12)
    # Hand-derived existing kp500: preserve -17.5Nm, not an encoder-zeroed0Nm.
    assert 500*(result.joint_targets['fr_calf_joint']-1.035) == pytest.approx(-17.5)
    # Keep actual measured stance anchors for slip checks; targets are commands.
    assert machine.anchors['fr_foot'][2] != pytest.approx(machine._targets['fr_foot'][2], abs=1e-6)


@pytest.mark.parametrize('bad', ['missing', 'nan', 'outside'])
def test_unverified_incomplete_or_invalid_handoff_emits_no_command(nav_robot_model, bad):
    state = bundle(nav_robot_model)
    held = {name: state.joints.data['position'][name] for name in nav_robot_model.joint_names}
    if bad == 'missing':
        held.pop('fr_calf_joint')
    else:
        held['fr_calf_joint'] = float('nan') if bad == 'nan' else 4.
    machine = CrawlMachine(nav_robot_model, default_limits())
    machine.reset(state, state.body.stamp_ns, state.body.received_ns, held_targets=held)
    result = machine.advance(state, (0., 0., 0.), state.body.stamp_ns, state.body.received_ns)
    assert result.state == 'FAULT' and result.joint_targets is None


@pytest.mark.parametrize('bad', ['missing', 'nan', 'duplicate'])
def test_cold_handoff_requires_one_finite_declared_position_seed(nav_robot_model, bad):
    from integrated_robot_navigation import model as model_api
    tree = ET.fromstring(nav_robot_model.urdf)
    control = tree.find('ros2_control')
    joint = control.find("joint[@name='fr_calf_joint']")
    initial = joint.find("state_interface[@name='position']/param[@name='initial_value']")
    if bad == 'missing':
        joint.find("state_interface[@name='position']").remove(initial)
    elif bad == 'nan':
        initial.text = 'nan'
    else:
        control.append(ET.fromstring(ET.tostring(joint)))
    changed = replace(nav_robot_model, urdf=ET.tostring(tree, encoding='unicode'))
    with pytest.raises(ValueError, match='initial leg'):
        model_api.initial_leg_targets(changed)
