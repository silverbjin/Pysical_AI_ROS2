"""ROS-free contract tests for Ch03 keyboard control input clamping."""
import ast
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"ros2_ws/src/my_robot_description/my_robot_description/simple_arm_teleop.py"
class TeleopStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=P.read_text()
        cls.parsed=ast.parse(cls.source)
    def test_clamp_algorithm_without_ros_import(self):
        fn=next(n for n in self.parsed.body if isinstance(n,ast.FunctionDef) and n.name=="constrain")
        isolated=ast.Module(body=[fn],type_ignores=[])
        namespace={}
        exec(compile(isolated,str(P),"exec"),namespace)
        clamp=namespace["constrain"]
        self.assertAlmostEqual(clamp(2,-1.57,1.57),1.57)
        self.assertAlmostEqual(clamp(-2,-1.57,1.57),-1.57)
        self.assertAlmostEqual(clamp(.25,-1.57,1.57),.25)
    def test_keyboard_contract_and_cleanup(self):
        self.assertIn("sys.stdin.isatty()",self.source)
        self.assertIn('if name != changed_joint:',self.source)
        self.assertIn('node.publish_commands(changed_joint)',self.source)
        self.assertIn('node.destroy_node()',self.source)
        self.assertIn('rclpy.shutdown()',self.source)
        self.assertIn('"/joint1/cmd_pos"',self.source)
        self.assertIn('"/joint2/cmd_pos"',self.source)
if __name__=="__main__": unittest.main()
