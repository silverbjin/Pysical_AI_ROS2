"""ROS-free §1.7 metadata consistency tests (owner's license remains unchanged)."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'robot_ws/src/my_robot_controller'


class TestMetadata(unittest.TestCase):
    def test_description_matches_manifest_and_setup(self):
        root = ElementTree.parse(PACKAGE / 'package.xml').getroot()
        description = root.findtext('description', '').strip()
        self.assertTrue(description)
        self.assertFalse(description.startswith('TODO'))
        source = (PACKAGE / 'setup.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        kwargs = {}
        for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
            if isinstance(call.func, ast.Name) and call.func.id == 'setup':
                kwargs = {k.arg: k.value for k in call.keywords}
                break
        self.assertEqual(ast.literal_eval(kwargs['description']), description)
        self.assertEqual(ast.literal_eval(kwargs['maintainer_email']),
                         root.find('maintainer').attrib['email'])

    def test_ros_dependencies_present(self):
        root = ElementTree.parse(PACKAGE / 'package.xml').getroot()
        dependencies = {n.text for n in root.findall('depend')}
        self.assertIn('rclpy', dependencies)
        # std_msgs is retained from the beginner's original pkg-create command.
        self.assertIn('std_msgs', dependencies)

    def test_license_fields_stay_aligned(self):
        root = ElementTree.parse(PACKAGE / 'package.xml').getroot()
        source = (PACKAGE / 'setup.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'setup']
        self.assertEqual(len(calls), 1)
        fields = {k.arg: k.value for k in calls[0].keywords}
        self.assertEqual(ast.literal_eval(fields['license']), root.findtext('license'))


if __name__ == '__main__':
    unittest.main()
