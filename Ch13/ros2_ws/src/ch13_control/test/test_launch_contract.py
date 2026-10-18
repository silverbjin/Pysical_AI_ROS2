import pytest
from ch13_control.launch_contract import validate_options

def test_safe_default_and_exclusive_backend():
    assert validate_options()['enabled'] is False
    assert validate_options(backend='mujoco')['backend']=='mujoco'
    assert validate_options(backend='gazebo')['backend']=='gazebo'
    with pytest.raises(ValueError):validate_options(backend='both')
    with pytest.raises(ValueError):validate_options(backend='other')
