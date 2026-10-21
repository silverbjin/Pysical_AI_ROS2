"""ROS-independent regression tests of joint-state message validation."""
import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'manipulation_basics'
spec = importlib.util.spec_from_file_location('valid', ROOT / 'joint_state_validation.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
extract = mod.extract_joint_measurement


def test_syntax_both_modules():
    for name in ['joint_state_validation.py', 'joint_state_listener.py']:
        compile(ast.parse((ROOT / name).read_text()), name, 'exec')


def test_joint_order_is_name_based():
    assert extract(['joint2', 'joint1'], [0.5, 0.0], [1.2, 2.0], 'joint2') == (0.5, 1.2)


@pytest.mark.parametrize('names,pos,vel', [
    ([], [], []), (['joint2'], [], []),
    (['joint1'], [0], []), (['joint2'], [float('nan')], []),
])
def test_missing_or_bad_position_is_safe(names, pos, vel):
    assert extract(names, pos, vel, 'joint2') is None


def test_missing_or_short_velocity_is_unknown():
    assert extract(['joint2'], [0.5], [], 'joint2') == (0.5, None)
    assert extract(['joint1', 'joint2'], [0, 0.5], [0.0], 'joint2') == (0.5, None)
    assert extract(['joint2'], [0.5], [float('inf')], 'joint2') == (0.5, None)


def test_throttled_logging_contract():
    text = (ROOT / 'joint_state_listener.py').read_text()
    assert 'time.monotonic()' in text
    assert 'now - self._last_log < self.log_period' in text
