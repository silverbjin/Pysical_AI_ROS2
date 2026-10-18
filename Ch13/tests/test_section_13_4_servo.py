"""Compare the projection Jacobian to an independent native MuJoCo camera."""
import math
from pathlib import Path
import subprocess

import mujoco
import numpy as np
import pytest

from integrated_robot_vision.contracts import Intrinsics
from integrated_robot_vision.kinematics import KinematicChain
from integrated_robot_vision.servo import projection_jacobian, servo_target, project_target

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/integrated_robot_description'
K = Intrinsics(320, 240, 277.128129211, 277.128129211, 160., 120., 'camera_optical_frame', 'test')
ARM = tuple(f'arm_joint_{i}' for i in range(1, 7))


@pytest.fixture
def chain():
    xml = subprocess.run(['xacro', str(PKG / 'urdf/robot_system.urdf.xacro'), 'vision_enabled:=true'],
                         text=True, capture_output=True, check=True).stdout
    return KinematicChain.from_urdf(xml)


def native_pixel(q, target_base):
    model = mujoco.MjModel.from_xml_path(str(PKG / 'mujoco/robot_system.xml'))
    data = mujoco.MjData(model)
    for name, value in q.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        data.qpos[model.jnt_qposadr[jid]] = value
    mujoco.mj_forward(model, data)
    camera = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, 'eye_in_hand')
    base = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'base_link')
    gl = data.cam_xmat[camera].reshape(3, 3).T @ (target_base+data.xpos[base]-data.cam_xpos[camera])
    optical = gl * [1., -1., -1.]
    return np.array([K.fx*optical[0]/optical[2]+K.cx, K.fy*optical[1]/optical[2]+K.cy])


def test_projection_jacobian_matches_independent_native_camera_and_signs(chain):
    q = dict.fromkeys(ARM, 0.)
    point = np.array([.03+math.sqrt(3)/2, 0., .34])
    jacobian = projection_jacobian(chain, q, point, K)
    independent = []
    for name in ('arm_joint_1', 'arm_joint_5'):
        plus, minus = q.copy(), q.copy()
        plus[name], minus[name] = 1e-5, -1e-5
        independent.append((native_pixel(plus, point)-native_pixel(minus, point))/2e-5)
    np.testing.assert_allclose(jacobian, np.column_stack(independent), atol=1e-5)
    assert jacobian[0, 0] > 200 and jacobian[1, 1] < -200
    assert np.linalg.matrix_rank(jacobian) == 2


def test_step_reduces_pixel_error_and_only_two_named_joints_change(chain):
    q = dict.fromkeys(ARM, 0.)
    q['arm_joint_2'], q['arm_joint_3'] = .01, -.01
    target = np.array([.90, .02, .35])
    desired = servo_target(chain, q, target, K, .2)
    assert desired is not None
    before = np.linalg.norm(project_target(chain, q, target, K)-[K.cx, K.cy])
    after = np.linalg.norm(project_target(chain, desired, target, K)-[K.cx, K.cy])
    assert after < before
    assert all(desired[name] == q[name] for name in ARM if name not in ('arm_joint_1', 'arm_joint_5'))
    assert q['arm_joint_1'] == q['arm_joint_5'] == 0.


def test_position_velocity_and_long_pause_limits(chain):
    for start in (0., .04, -.04):
        q = dict.fromkeys(ARM, 0.)
        q['arm_joint_1'] = q['arm_joint_5'] = start
        desired = servo_target(chain, q, np.array([.90, .3, .30]), K, 10.)
        assert desired is not None
        for name in ('arm_joint_1', 'arm_joint_5'):
            assert abs(desired[name]) <= .04
            assert abs(desired[name]-q[name]) <= .02+1e-12


@pytest.mark.parametrize('dt', [0., -.1, math.nan, math.inf])
def test_invalid_time_rejects_command(chain, dt):
    assert servo_target(chain, dict.fromkeys(ARM, 0.), np.array([.9, 0., .34]), K, dt) is None


def test_behind_camera_missing_and_reordered_control_names_rejected(chain):
    q = dict.fromkeys(ARM, 0.)
    assert servo_target(chain, q, np.array([-.9, 0., 2.]), K, .2) is None
    assert servo_target(chain, {'arm_joint_1': 0.}, np.array([.9, 0., .34]), K, .2) is None
    with pytest.raises(ValueError):
        projection_jacobian(chain, q, np.array([.9, 0., .34]), K,
                             joints=('arm_joint_5', 'arm_joint_1'))


def test_collinear_camera_control_axes_are_singular_and_refused():
    links = ['<link name="base_link"/>']
    parent = 'base_link'
    for i in range(1, 7):
        child = f'link_{i}'
        links.append(f'<link name="{child}"/><joint name="arm_joint_{i}" type="revolute">'
                     f'<parent link="{parent}"/><child link="{child}"/><axis xyz="0 0 1"/>'
                     '<limit lower="-1" upper="1"/></joint>')
        parent = child
    links.append('<link name="camera_optical_frame"/><joint name="optical" type="fixed">'
                 f'<parent link="{parent}"/><child link="camera_optical_frame"/></joint>')
    chain = KinematicChain.from_urdf('<robot>' + ''.join(links) + '</robot>')
    assert servo_target(chain, dict.fromkeys(ARM, 0.), np.array([.1, .1, 1.]), K, .2) is None
