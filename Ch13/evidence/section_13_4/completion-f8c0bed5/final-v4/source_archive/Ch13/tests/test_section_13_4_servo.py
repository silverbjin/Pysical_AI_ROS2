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
from integrated_robot_vision.servo import camera_motion_target

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


@pytest.mark.parametrize('positions', [(.01,-.02,.03,-.01,.02,.04),
                                      (-.02,.01,-.03,.02,-.01,-.02)])
def test_compiled_camera_kinematics_and_jacobian_match_native_at_nonzero_pose(chain, positions):
    q = dict(zip(ARM,positions))
    pose, axes = chain.camera_kinematics(q)
    assert pose.shape == (4,4) and set(axes) == set(ARM)
    target = np.array([.90,.02,.35])
    pixel = project_target(chain,q,target,K)
    np.testing.assert_allclose(pixel,native_pixel(q,target),atol=1e-6)
    columns=[]
    for name in ('arm_joint_1','arm_joint_5'):
        plus,minus=q.copy(),q.copy()
        plus[name]+=1e-5
        minus[name]-=1e-5
        columns.append((native_pixel(plus,target)-native_pixel(minus,target))/2e-5)
    np.testing.assert_allclose(projection_jacobian(chain,q,target,K),
                               np.column_stack(columns),atol=1e-5)


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


def test_explicit_camera_motion_fixture_has_two_second_period_and_bounded_steps():
    q = dict.fromkeys(ARM, 0.)
    values = []
    for elapsed in np.arange(0., 4., .2):
        desired = camera_motion_target(q, elapsed, .2)
        assert desired is not None
        assert abs(desired['arm_joint_1']) <= .03
        assert abs(desired['arm_joint_1']-q['arm_joint_1']) <= .02+1e-12
        assert all(desired[n] == q[n] for n in ARM[1:])
        assert desired['arm_joint_1'] == pytest.approx(.03*math.sin(math.pi*(elapsed+.2)))
        values.append(desired['arm_joint_1'])
        q = desired
    np.testing.assert_allclose(values[:10], values[10:], atol=1e-12)
    assert camera_motion_target(q, float('nan'), .2) is None
    assert camera_motion_target(q, 0., -.1) is None
