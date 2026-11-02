"""Control-message fixtures test arithmetic only, never establish native origin."""
from copy import deepcopy
import xml.etree.ElementTree as ET
import pytest
from integrated_robot_navigation.geometry import navigation_mjcf
from test_native_verdicts import api


def records(model, xml):
    joints = {j.get('name'): j for j in ET.fromstring(model.urdf).findall('joint')}
    actuators = []
    for i, element in enumerate(ET.fromstring(xml).find('actuator')):
        name = element.get('joint')
        lo, hi, _, _ = model.limits[name]
        q = min(hi, max(lo, 0.))
        actuators.append(dict(actuator_id=i, ctrl_index=i, output_index=i, joint_name=name,
            joint_type='slide' if joints[name].get('type') == 'prismatic' else 'hinge',
            control_kind='position', position=q, velocity=0., ctrl=q,
            actuator_force=0., joint_force=0., kp=float(element.get('kp')), kv=float(element.get('kv')),
            gear=1., force_limited=True, ctrl_limited=True,
            force_range=list(map(float, element.get('forcerange').split())),
            ctrl_range=list(map(float, element.get('ctrlrange').split()))))
    return [dict(schema=1, epoch=0, capture_ns=(i+1)*20_000_000, sequence=i+1,
                 actuators=deepcopy(actuators), stage='stand') for i in range(30)]


def test_complete_scalar_native_controls_match_physics(nav_robot_model):
    xml = navigation_mjcf(nav_robot_model)
    assert api().assess_native_controls(records(nav_robot_model, xml), nav_robot_model, xml)


@pytest.mark.parametrize('change', ['duplicate_capture', 'missing_joint', 'duplicate_address',
    'wrong_gain', 'wrong_unit', 'effort_overflow', 'nonfinite', 'disabled_force_limit'])
def test_native_controls_fail_closed_on_wrong_engine_mapping(nav_robot_model, change):
    xml = navigation_mjcf(nav_robot_model)
    values = records(nav_robot_model, xml)
    row, actuator = values[-1], values[-1]['actuators'][0]
    if change == 'duplicate_capture': row['capture_ns'] = values[-2]['capture_ns']
    if change == 'missing_joint': row['actuators'].pop()
    if change == 'duplicate_address': actuator['ctrl_index'] = row['actuators'][1]['ctrl_index']
    if change == 'wrong_gain': actuator['kp'] *= 2
    if change == 'wrong_unit': actuator['joint_type'] = 'slide'
    if change == 'effort_overflow': actuator['actuator_force'] = 1000.
    if change == 'nonfinite': actuator['ctrl'] = float('nan')
    if change == 'disabled_force_limit': actuator['force_limited'] = False
    assert not api().assess_native_controls(values, nav_robot_model, xml)
