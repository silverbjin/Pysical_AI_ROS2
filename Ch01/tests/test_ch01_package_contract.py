"""Offline static checks of the Ch01 §1.5 Python package contract.

No ros2/rclpy/colcon imports; does not execute setup.py.
Run: python3 -m unittest discover -s Ch01/tests -p 'test_*.py' -v
"""
from __future__ import annotations

import ast
import configparser
from pathlib import Path
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'robot_ws/src/my_robot_controller'


class TestPackageContract(unittest.TestCase):
    def test_manifest_name_and_build_type(self):
        root = ElementTree.parse(PACKAGE / 'package.xml').getroot()
        self.assertEqual(root.findtext('name'), 'my_robot_controller')
        self.assertEqual(root.findtext('export/build_type'), 'ament_python')
        self.assertIn('rclpy', [n.text for n in root.findall('depend')])

    def test_ros_executable_entry_point(self):
        tree = ast.parse((PACKAGE / 'setup.py').read_text(encoding='utf-8'))
        scripts = [n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertIn('test_node = my_robot_controller.simple_controller:main', scripts)

    def test_setup_cfg_install_location(self):
        parser = configparser.ConfigParser()
        parser.read(PACKAGE / 'setup.cfg', encoding='utf-8')
        self.assertEqual(parser.get('develop', 'script_dir'), '$base/lib/my_robot_controller')
        self.assertEqual(parser.get('install', 'install_scripts'), '$base/lib/my_robot_controller')

    def test_entry_source_resource_exist_and_parse(self):
        source = PACKAGE / 'my_robot_controller/simple_controller.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        functions = {n.name for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue({'main', 'timer_callback', '__init__'}.issubset(functions))
        self.assertTrue((PACKAGE / 'resource/my_robot_controller').is_file())


if __name__ == '__main__':
    unittest.main()
