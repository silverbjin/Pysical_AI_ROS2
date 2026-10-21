"""Ch10 Gazebo launch/bridge contract checks; safe without simulator runtime."""
import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
BRIDGE = PACKAGE / 'config' / 'ros_gz_bridge.yaml'
LAUNCH = PACKAGE / 'launch' / 'simulation.launch.py'
XACRO = PACKAGE / 'urdf' / 'robot.urdf.xacro'


def test_launch_parse_and_clock():
    code = LAUNCH.read_text(encoding='utf-8')
    ast.parse(code)
    assert "DeclareLaunchArgument('use_sim_time', default_value='true')" in code
    assert "LaunchConfiguration('use_sim_time')" in code


def test_ros_gz_joint_command_bridge():
    yaml_text = BRIDGE.read_text(encoding='utf-8')
    assert len(re.findall(r'direction: ROS_TO_GZ', yaml_text)) == 12
    assert len(re.findall(r'ros_type_name: "std_msgs/msg/Float64"', yaml_text)) == 12
    assert len(re.findall(r'gz_type_name: "gz.msgs.Double"', yaml_text)) == 12
    assert yaml_text.count('/cmd_pos') == 24  # ROS and GZ name each
    assert '/joint_commands' not in yaml_text


def test_xacro_wellformed():
    ET.parse(XACRO)
    ET.parse(PACKAGE / 'urdf' / 'parts' / 'leg.xacro')
    ET.parse(PACKAGE / 'urdf' / 'common' / 'robot_properties.xacro')
