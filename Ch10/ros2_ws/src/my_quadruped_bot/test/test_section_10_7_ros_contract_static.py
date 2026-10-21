"""ROS 2 source-contract checks without requiring rclpy installed."""
import ast
from pathlib import Path
P = Path(__file__).resolve().parents[1] / 'my_quadruped_bot' / 'quadruped_controller_ros2.py'


def test_ast_and_command_topics():
    source = P.read_text(encoding='utf-8')
    ast.parse(source)
    assert 'create_publisher(Float64, topic, 10)' in source
    assert "create_publisher(JointState, 'joint_states'" not in source
    assert 'self.joint_pub.publish' not in source


def test_real_ik_and_freshness():
    source = P.read_text(encoding='utf-8')
    assert 'self.ik_solver.solve(' in source
    assert 'target_foot_pos[0] - hx' in source
    assert 'age > self.get_parameter' in source
    assert 'self.cmd_vel_target = [0.0, 0.0, 0.0]' in source


def test_parameters_atomic_validation():
    source = P.read_text(encoding='utf-8')
    assert "updates = {p.name: p.value for p in params}" in source
    assert 'self.gait_planner.set_gait' in source
    assert "publish_cmd_odom_tf" in source
