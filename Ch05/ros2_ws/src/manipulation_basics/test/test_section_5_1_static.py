"""Static package and controller contract test; run with pytest."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_package_xml_declares_runtime_dependencies():
    root = ET.parse(ROOT / 'package.xml').getroot()
    deps = {x.text for x in root.findall('exec_depend')}
    required = {'ros_gz_bridge', 'gz_ros2_control', 'xacro', 'robot_state_publisher',
                'rviz2', 'controller_manager', 'builtin_interfaces',
                'joint_trajectory_controller', 'joint_state_broadcaster'}
    assert required <= deps
    assert root.find('version').text == '0.0.1'


def test_controller_map_has_no_orphan_gripper():
    cfg = yaml.safe_load((ROOT / 'config/ros2_controllers.yaml').read_text())
    params = cfg['controller_manager']['ros__parameters']
    assert 'gripper_controller' not in params
    arm = cfg['arm_controller']['ros__parameters']
    assert arm['joints'] == ['joint1', 'joint2', 'joint3', 'joint4']
    assert arm['command_interfaces'] == ['position']
    assert arm['state_interfaces'] == ['position', 'velocity']
    assert 'open_loop_control' not in arm


def test_setup_version_synced():
    assert re.search(r"version=['\"]0\.0\.1['\"]", (ROOT / 'setup.py').read_text())
