import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
def read_and_parse(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    return ast.parse(source), source

class Section25(unittest.TestCase):
    def test_interface_contract_and_service_registration(self):
        from xml.etree import ElementTree
        tree, src = read_and_parse("ros2_ws/src/my_robot_system/my_robot_system/compute_rectangle_area_server.py")
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=="compute_area")
        ns = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "<area>", "exec"), ns)
        self.assertEqual(ns["compute_area"](2.0, 3.0), 6.0)
        self.assertEqual(ns["compute_area"](0.0, 3.0), 0.0)
        self.assertIn("ComputeRectangleArea", src)
        _, setup = read_and_parse("ros2_ws/src/my_robot_system/setup.py")
        self.assertIn("compute_rectangle_area_server = my_robot_system.compute_rectangle_area_server:main", setup)
        interface = (ROOT / "ros2_ws/src/my_robot_interfaces/srv/ComputeRectangleArea.srv").read_text()
        self.assertEqual(interface.split("---")[0].count("float64"), 2)
        self.assertEqual(interface.split("---")[1].count("float64"), 1)
        pkg = ElementTree.parse(ROOT / "ros2_ws/src/my_robot_interfaces/package.xml").getroot()
        self.assertIn("action_msgs", [n.text for n in pkg.findall("depend")])
if __name__ == "__main__": unittest.main()
