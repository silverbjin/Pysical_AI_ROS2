"""Independent axis checks and real MuJoCo/URDF transform parity."""
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest

from integrated_robot_vision.kinematics import KinematicChain

PKG = Path(__file__).resolve().parents[1] / 'ros2_ws/src/integrated_robot_description'


def expanded(enabled=True):
    return subprocess.run(['xacro', str(PKG / 'urdf/robot_system.urdf.xacro'),
                           f'vision_enabled:={str(enabled).lower()}'],
                          capture_output=True, text=True, check=True).stdout


def test_zero_pose_optical_principal_ray():
    chain = KinematicChain.from_urdf(expanded())
    q = {f'arm_joint_{i}': 0. for i in range(1, 7)}
    transform = chain.forward(q)
    np.testing.assert_allclose(transform[:3, 2], [math.sqrt(3)/2, 0, -.5], atol=1e-8)
    np.testing.assert_allclose(transform[:3, 3], [.03, 0, .84], atol=1e-8)


def test_left_up_pixel_signs_and_gl_basis():
    xml = expanded()
    chain = KinematicChain.from_urdf(xml, 'camera_sensor_frame', 'camera_optical_frame')
    rotation = chain.forward({})[:3, :3]
    np.testing.assert_allclose(rotation[:, 0], [0, -1, 0], atol=1e-8)
    np.testing.assert_allclose(rotation[:, 1], [0, 0, -1], atol=1e-8)
    model = mujoco.MjModel.from_xml_path(str(PKG / 'mujoco/robot_system.xml'))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    cid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, 'eye_in_hand')
    assert cid >= 0
    np.testing.assert_allclose(-data.cam_xmat[cid].reshape(3, 3)[:, 2],
                               [math.sqrt(3)/2, 0, -.5], atol=1e-8)


@pytest.mark.parametrize('positions', [[0]*6, [.03, -.02, .01, .02, -.03, .01]])
def test_camera_extrinsic_parity(positions):
    xml = expanded()
    tree = ET.fromstring(xml)
    assert len([j for j in tree.findall('joint') if j.get('type') != 'fixed']) == 20
    chain = KinematicChain.from_urdf(xml)
    q = dict(zip([f'arm_joint_{i}' for i in range(1, 7)], positions))
    expected = chain.forward(q)
    model = mujoco.MjModel.from_xml_path(str(PKG / 'mujoco/robot_system.xml'))
    data = mujoco.MjData(model)
    for name, value in q.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        data.qpos[model.jnt_qposadr[jid]] = value
    mujoco.mj_forward(model, data)
    bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'camera_optical_frame')
    base = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'base_link')
    assert bid >= 0
    np.testing.assert_allclose(data.xpos[bid] - data.xpos[base], expected[:3, 3], atol=1e-8)
    np.testing.assert_allclose(data.xmat[bid].reshape(3, 3), expected[:3, :3], atol=1e-8)
    # Deliberately reorder insertion order: FK must use names, not dict order.
    np.testing.assert_allclose(chain.forward(dict(reversed(list(q.items())))), expected)


def test_missing_joint_and_bad_tree_rejected():
    chain = KinematicChain.from_urdf(expanded())
    with pytest.raises(ValueError):
        chain.forward({'arm_joint_1': 0.})
    with pytest.raises(ValueError):
        KinematicChain.from_urdf('<robot><link name="a"/></robot>')


def test_vision_off_preserves_legacy_model_and_on_adds_native_sensor():
    off, on = ET.fromstring(expanded(False)), ET.fromstring(expanded(True))
    assert off.findall('.//sensor') == []
    sensor = on.find('.//sensor')
    assert sensor is not None and sensor.get('type') == 'rgbd_camera'
    assert sensor.find('camera/image/width').text == '320'
    model = mujoco.MjModel.from_xml_path(str(PKG / 'mujoco/vision_fixture.xml'))
    assert model.nu == 20
    assert mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, 'vision_fixture') >= 0


def test_native_pose_preserves_observed_stamp_and_rejects_bad_quaternion():
    from geometry_msgs.msg import Pose, Twist
    from builtin_interfaces.msg import Time
    from integrated_robot_vision.native_pose import make_odometry
    pose, twist = Pose(), Twist()
    pose.position.z = .46
    pose.orientation.w = 1.
    stamp = Time(sec=2, nanosec=123)
    out = make_odometry(pose, twist, stamp)
    assert out.header.stamp == stamp
    assert out.header.frame_id == 'odom'
    assert out.child_frame_id == 'base_footprint'
    assert out.pose.pose.position.z == .46
    pose.position.z = 99
    assert out.pose.pose.position.z == .46
    pose.orientation.w = 0.
    with pytest.raises(ValueError):
        make_odometry(pose, twist, stamp)


def test_mujoco_vision_config_keeps_one_native_parameter_file():
    import importlib.util
    import yaml
    spec = importlib.util.spec_from_file_location('mujoco_launch', PKG / 'launch/mujoco.launch.py')
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    path = launch.materialize_controller_config(PKG / 'config/controllers.yaml',
                                                PKG / 'config/mujoco_vision_plugins.yaml')
    merged = yaml.safe_load(Path(path).read_text())
    assert merged['controller_manager']['ros__parameters']['update_rate'] == 100
    plugins = merged['/**']['ros__parameters']['mujoco_plugins']
    assert plugins['eye_camera']['eye_in_hand']['policy'] == 'streaming'
    assert plugins['eye_camera']['overview']['policy'] == 'disabled'
    assert Path(path).parent == Path('/tmp')


def test_native_mujoco_clipping_is_metric_not_extent_scaled():
    model = mujoco.MjModel.from_xml_path(str(PKG / 'mujoco/vision_fixture.xml'))
    assert model.vis.map.znear * model.stat.extent == pytest.approx(.1)
    assert model.vis.map.zfar * model.stat.extent == pytest.approx(5.)
