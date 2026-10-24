"""Synthetic metadata fixtures do not establish native process/message origin."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

from integrated_robot_navigation import scene
from integrated_robot_navigation.model import compile_model
from test_native_verdicts import api


@pytest.fixture(scope='module')
def generated_controls(tmp_path_factory):
    record = scene.materialize_scene('gazebo','g1',tmp_path_factory.mktemp('gz_metadata')/'scene')
    model = compile_model(Path(record['robot']['path']).read_text())
    tree = ET.fromstring(model.urdf)
    joints = {joint.get('name'):joint for joint in tree.findall('joint')}
    rows = []
    for index,name in enumerate(model.limits):
        low,high,speed,effort = model.limits[name]
        kind = 'slide' if joints[name].get('type') == 'prismatic' else 'hinge'
        native = tree.find(f"ros2_control/joint[@name='{name}']/param[@name='ch13_native_damping']")
        rows.append(dict(entity=index+100,name=name,type=kind,
            axis_joint=list(map(float,joints[name].find('axis').get('xyz').split())),
            position=max(low,min(high,0.)),velocity=0.,lower=low,upper=high,
            effort_limit=effort,velocity_limit=speed,native_damping=float(native.text),
            position_unit='m' if kind == 'slide' else 'rad',
            velocity_unit='m/s' if kind == 'slide' else 'rad/s',effort_unit='N' if kind == 'slide' else 'Nm',
            velocity_command=None,force_command=0.,transmitted_force_joint=[0.,0.,0.],
            transmitted_torque_joint=[0.,0.,0.],projected_transmitted_effort=0.,applied_generalized_force=None))
    packets = [dict(schema=2,engine='gazebo',epoch=0,sequence=i+1,capture_ns=(i+1)*20_000_000,
        sample_phase='pre_physics',state_capture_ns=(i+1)*20_000_000-2_000_000,step_ns=2_000_000,
        joints=deepcopy(rows)) for i in range(30)]
    return model,Path(record['world']['path']).read_text(),packets


@pytest.mark.parametrize('fault',['','missing_joint','duplicate_entity','wrong_unit','force_overflow',
    'velocity_owner','wrong_damping','wrong_axis','nonfinite','duplicate_capture','wrong_phase',
    'wrong_state_time','wrong_step','projected_wrench','empty'])
def test_native_gazebo_scalar_force_contract_is_not_mujoco_or_declared_ready(generated_controls,fault):
    model,world,original = generated_controls
    packets = deepcopy(original)
    row,joint = packets[-1],packets[-1]['joints'][0]
    if fault == 'missing_joint': row['joints'].pop()
    elif fault == 'duplicate_entity': joint['entity'] = row['joints'][1]['entity']
    elif fault == 'wrong_unit': joint['effort_unit'] = 'm'
    elif fault == 'force_overflow': joint['force_command'] = joint['effort_limit']+.01
    elif fault == 'velocity_owner': joint['velocity_command'] = 0.
    elif fault == 'wrong_damping': joint['native_damping'] += .01
    elif fault == 'wrong_axis': joint['axis_joint'] = [0.,0.,0.]
    elif fault == 'nonfinite': joint['position'] = float('nan')
    elif fault == 'duplicate_capture': row['capture_ns'] = packets[-2]['capture_ns']
    elif fault == 'wrong_phase': row['sample_phase'] = 'post_physics'
    elif fault == 'wrong_state_time': row['state_capture_ns'] = row['capture_ns']
    elif fault == 'wrong_step': row['step_ns'] *= 2
    elif fault == 'projected_wrench': joint['projected_transmitted_effort'] = 1.
    elif fault == 'empty': packets = []
    assert hasattr(api(),'assess_gazebo_controls'), 'Gazebo native force verdict missing'
    assert api().assess_gazebo_controls(packets,model,world) is (fault == '')
