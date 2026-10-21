"""ROS-free policy/goal tests."""
import ast
from pathlib import Path
import math
import pytest

PATH = Path(__file__).resolve().parents[1] / 'manipulation_basics/simple_joint_controller.py'
SOURCE = PATH.read_text()
TREE = ast.parse(SOURCE)


def load_validator():
    import_nodes = [n for n in TREE.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'validate_goal']
    values = {}
    for assign in TREE.body:
        if isinstance(assign, ast.Assign):
            for target in assign.targets:
                if isinstance(target, ast.Name) and target.id in (
                        'JOINT_NAMES', 'JOINT_LIMITS', 'BENDING', 'HOME'):
                    values[target.id] = ast.literal_eval(assign.value)
    values['math'] = math
    exec(compile(ast.Module(body=import_nodes, type_ignores=[]), '<validator>', 'exec'), values)
    return values['validate_goal']


def test_syntax():
    compile(TREE, '<controller>', 'exec')


def test_subscriber_and_zero_velocity():
    assert 'get_subscription_count() == 0' in SOURCE
    assert 'point.velocities = [0.0] * len(JOINT_NAMES)' in SOURCE


@pytest.mark.parametrize('bad', [[0, 0, 0], [0, 0, 0, 99],
                               [float('nan'), 0, 0, 0], [float('inf'), 0, 0, 0]])
def test_reject_invalid_goals(bad):
    with pytest.raises(ValueError):
        load_validator()(bad)


def test_valid_goals():
    assert load_validator()([0, 0, 0, 0]) == [0, 0, 0, 0]
    assert load_validator()([0, 0.5, 0.5, 1.0]) == [0, 0.5, 0.5, 1.0]
