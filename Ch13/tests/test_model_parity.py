from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from ch13_sim_core.contract import load_contract
from ch13_sim_core.model_validation import load_urdf_joints, load_mjcf_joints, validate_model_parity

ROOT = Path(__file__).parents[1]
XACRO = ROOT/'ros2_ws/src/ch13_robot_description/urdf/integrated_robot.urdf.xacro'
MJCF = ROOT/'src/ch13_sim_core/models/integrated_robot.xml'

@pytest.fixture
def expanded(): return subprocess.check_output(['xacro',str(XACRO)], text=True)

def test_model_parity(expanded):
    c = load_contract()
    u, m = load_urdf_joints(expanded), load_mjcf_joints(MJCF)
    validate_model_parity(c, u, m)
    assert len(u) == len(m) == 20
    for name, axis in [('fr_hip_joint',(1,0,0)),('fr_thigh_joint',(0,1,0)),('arm_joint_1',(0,0,1)),('arm_joint_3',(0,1,0)),('arm_joint_4',(1,0,0)),('arm_joint_6',(0,0,1)),('gripper_right_joint',(0,-1,0))]:
        np.testing.assert_allclose(u[name].axis,axis)

def test_axis_mutation_fails_parity(expanded, tmp_path):
    tree = ET.parse(MJCF)
    tree.find(".//joint[@name='arm_joint_3']").set('axis','1 0 0')
    bad = tmp_path/'bad.xml'
    tree.write(bad)
    with pytest.raises(ValueError,match='arm_joint_3'):
        validate_model_parity(load_contract(),load_urdf_joints(expanded),load_mjcf_joints(bad))

def test_unique_root_positive_inertias(expanded):
    root = ET.fromstring(expanded)
    links = [x.get('name') for x in root.findall('link')]
    joints = [x.get('name') for x in root.findall('joint')]
    assert len(links) == len(set(links))
    assert len(joints) == len(set(joints))
    assert set(links)-{j.find('child').get('link') for j in root.findall('joint')} == {'base_footprint'}
    for link in root.findall('link'):
        inertial = link.find('inertial')
        assert float(inertial.find('mass').get('value')) > 0
        i = inertial.find('inertia')
        assert all(float(i.get(k)) > 0 for k in ('ixx','iyy','izz'))

def test_mount_transform_parity(expanded, tmp_path):
    tree = ET.parse(MJCF)
    tree.find(".//body[@name='arm_mount']").set('pos','0 0 0.095')
    bad = tmp_path/'mount.xml'
    tree.write(bad)
    with pytest.raises(ValueError,match='mount'):
        validate_model_parity(load_contract(),load_urdf_joints(expanded),load_mjcf_joints(bad))
