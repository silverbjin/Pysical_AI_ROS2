"""ROS package manifest and entry-point contract tests without ROS installation."""
import ast
from pathlib import Path
import xml.etree.ElementTree as ET

PACKAGE = Path(__file__).resolve().parents[1]


def test_manifest_xml_and_runtime_dependencies():
    root = ET.parse(PACKAGE / 'package.xml').getroot()
    depends = {e.text for e in root if e.tag in ('depend', 'exec_depend')}
    required = {'rclpy', 'std_msgs', 'geometry_msgs', 'sensor_msgs',
                'nav_msgs', 'tf2_ros', 'ros_gz_sim', 'ros_gz_bridge',
                'robot_state_publisher', 'xacro'}
    assert required <= depends


def test_python_entry_points_and_sources_are_present():
    setup_code = (PACKAGE / 'setup.py').read_text(encoding='utf-8')
    ast.parse(setup_code)
    for name in ('quadruped_controller', 'trot_controllerFSM', 'stand_up'):
        assert name + ' =' in setup_code
    assert (PACKAGE / 'my_quadruped_bot' / 'quadruped_controller.py').exists()


def test_bridged_command_contract():
    content = (PACKAGE / 'config' / 'ros_gz_bridge.yaml').read_text(encoding='utf-8')
    assert content.count('direction: ROS_TO_GZ') == 12
    assert 'std_msgs/msg/Float64' in content
