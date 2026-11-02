"""Breaks: scene omission/overwrites, fake body actuation, unsafe ray masks."""
import hashlib
import importlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
import xacro

from integrated_robot_navigation.geometry import description_dir


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.scene'), 'scene implementation missing'
    return importlib.import_module('integrated_robot_navigation.scene')


@pytest.mark.parametrize('engine', ['mujoco', 'gazebo'])
def test_native_scene_materializes_bound_files_without_overwrite(tmp_path, engine):
    output = tmp_path / engine
    record = api().materialize_scene(engine, 'detour', output)
    assert record['engine'] == engine
    for key in ('world', 'map', 'robot'):
        file = Path(record[key]['path'])
        assert file.is_file() and file.is_relative_to(output)
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record[key]['sha256']
    with pytest.raises(FileExistsError):
        api().materialize_scene(engine, 'detour', output)


def test_mujoco_sensor_physics_and_robot_ray_mask_are_native(tmp_path):
    import mujoco
    record = api().materialize_scene('mujoco', 'front', tmp_path/'scene')
    tree = ET.parse(record['world']['path'])
    assert not tree.findall('.//plugin')  # body/root commands cannot hide in MJCF
    m = mujoco.MjModel.from_xml_path(record['world']['path'])
    for name in ('navigation_accelerometer', 'navigation_gyro'):
        assert m.sensor(name).dim[0] == 3
    assert m.body('fr_hip_link').pos[1] == pytest.approx(-.13)
    for i in range(m.ngeom):
        assert m.geom_group[i] == (1 if m.geom_bodyid[i] != 0 else 0)
    for actuator in tree.findall('actuator/*'):
        assert actuator.get('joint') not in ('root', 'base_link')
    assert m.geom('cup_bottom').id >= 0 and m.geom('table').id >= 0


def test_nav_xacro_opt_in_has_sensors_and_preserves_legacy_default():
    file = description_dir()/'urdf/robot_system.urdf.xacro'
    legacy = ET.fromstring(xacro.process_file(str(file), mappings={'control_backend': 'gazebo'}).toxml())
    assert not legacy.findall('.//sensor[@name="navigation_lidar"]')
    nav = ET.fromstring(xacro.process_file(str(file), mappings={
        'control_backend': 'gazebo', 'navigation_enabled': 'true', 'hip_mount_y': '.13'}).toxml())
    lidar = nav.find('.//sensor[@name="navigation_lidar"]')
    assert lidar is not None
    assert float(lidar.findtext('update_rate')) == 10.
    assert int(lidar.findtext('lidar/scan/horizontal/samples')) == 360
    assert lidar.findtext('lidar/visibility_mask') == '1'
    assert nav.find('.//sensor[@type="imu"]') is not None


def test_unknown_scene_is_rejected_before_creating_output(tmp_path):
    output = tmp_path/'unknown'
    with pytest.raises(ValueError):
        api().materialize_scene('mujoco', 'stairs', output)
    assert not output.exists()


def test_gazebo_collision_map_comes_from_actual_fixed_joint_conversion(tmp_path):
    record = api().materialize_scene('gazebo', 'g1', tmp_path/'native')
    sdf = ET.parse(record['robot_sdf']['path'])
    actual = {f"integrated_robot::{link.get('name')}::{collision.get('name')}"
              for link in sdf.findall('.//model/link') for collision in link.findall('collision')}
    mapping = record['foot_collision_map']
    assert set(mapping.values()) == {'fr_foot', 'fl_foot', 'rr_foot', 'rl_foot'}
    assert len(mapping) == 4 and set(mapping).issubset(actual)


def test_nav_gazebo_position_system_binds_gains_without_changing_legacy_hardware(tmp_path):
    record = api().materialize_scene('gazebo', 'g1', tmp_path/'pd_scene')
    root = ET.parse(record['robot']['path']).getroot()
    control = root.find('ros2_control')
    assert control.findtext('hardware/plugin') == 'integrated_robot_navigation_sensors/PositionPDSystem'
    expected = {
        'hip': (200., 4.47213595499958), 'thigh': (500., 8.94427190999916),
        'calf': (750., 10.954451150103322), 'arm_joint_1': (120., 25.),
        'arm_joint_2': (120., 25.), 'arm_joint_3': (105., 40.),
        'arm_joint_4': (75., 15.), 'arm_joint_5': (67.5, 15.), 'arm_joint_6': (60., 10.),
        'gripper_left_joint': (100., 15.), 'gripper_right_joint': (100., 15.)}
    assert len(control.findall('joint')) == 20
    for joint in control.findall('joint'):
        name = joint.get('name')
        key = name.split('_')[1] if name[:3] in ('fr_', 'fl_', 'rr_', 'rl_') else name
        assert (float(joint.findtext("param[@name='ch13_kp']")),
                float(joint.findtext("param[@name='ch13_kd']"))) == expected[key]
        assert [v.get('name') for v in joint.findall('command_interface')] == ['position']
        physical = root.find(f"joint[@name='{name}']/limit")
        # Existing physical caps remain the original model values, not PD gains.
        assert float(physical.get('effort')) == (20. if key == 'hip' else
            30. if key in ('thigh', 'calf', 'arm_joint_3') else
            35. if key in ('arm_joint_1', 'arm_joint_2') else
            20. if key == 'arm_joint_4' else 12. if key == 'arm_joint_6' else 15.)
    legacy = ET.fromstring(xacro.process_file(str(description_dir()/'urdf/robot_system.urdf.xacro'),
        mappings={'control_backend': 'gazebo'}).toxml())
    assert legacy.findtext('ros2_control/hardware/plugin') == 'gz_ros2_control/GazeboSimSystem'


def test_gazebo_damping_is_native_model_bound_and_not_double_counted(tmp_path):
    record = api().materialize_scene('gazebo', 'g1', tmp_path/'native_damping')
    root = ET.parse(record['robot']['path']).getroot()
    legacy = ET.fromstring(xacro.process_file(str(description_dir()/'urdf/robot_system.urdf.xacro'),
        mappings={'control_backend': 'gazebo'}).toxml())
    for joint in root.findall('ros2_control/joint'):
        name = joint.get('name')
        original = legacy.find(f"joint[@name='{name}']/dynamics")
        base = float(original.get('damping', '0')) if original is not None else 0.
        kd = float(joint.findtext("param[@name='ch13_kd']"))
        assert joint.findtext("param[@name='ch13_damping_mode']") == 'native'
        assert float(joint.findtext("param[@name='ch13_base_damping']")) == base
        assert float(joint.findtext("param[@name='ch13_native_damping']")) == pytest.approx(base+kd)
        actual = root.find(f"joint[@name='{name}']/dynamics")
        assert float(actual.get('damping')) == pytest.approx(base+kd)
