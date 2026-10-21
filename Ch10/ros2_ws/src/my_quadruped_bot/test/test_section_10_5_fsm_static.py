"""Static AST checks for the ROS-dependent 10.5 FSM module (no rclpy needed)."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'my_quadruped_bot' / 'trot_controllerFSM.py'


def test_fsm_source_parses():
    ast.parse(SOURCE.read_text(encoding='utf-8'))


def test_duty_and_coordinate_contract():
    source = SOURCE.read_text(encoding='utf-8')
    assert 'duty_factor / current_freq' in source
    assert "'FL': ( 0.25,  0.10)" in source
    assert "'FR': ( 0.25, -0.10)" in source
    assert 'self.cmd_timeout_sec = 0.5' in source


def test_parameter_bounds_and_watchdog():
    source = SOURCE.read_text(encoding='utf-8')
    assert '0.05 <= param.value <= 4.0' in source
    assert '0.0 <= param.value <= 0.12' in source
    assert 'age > self.cmd_timeout_sec' in source
