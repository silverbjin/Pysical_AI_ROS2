"""Static launch contract checks without ROS."""
import ast
from pathlib import Path
SOURCE = (Path(__file__).resolve().parents[1] / 'launch/manipulation_system.launch.py').read_text()
TREE = ast.parse(SOURCE)


def test_valid_python_and_checked_exit_return_code():
    compile(TREE, '<launch>', 'exec')
    assert 'event.returncode == 0' in SOURCE
    assert 'Shutdown(reason=reason)' in SOURCE


def test_no_arbitrary_sleep_or_start_event_gate():
    assert 'OnProcessStart' not in SOURCE
    assert 'TimerAction' not in SOURCE
    assert 'OnProcessExit(target_action=spawn' in SOURCE
    assert 'OnProcessExit(target_action=jsb' in SOURCE


def test_full_controller_and_clock_contract():
    for text in ('joint_state_broadcaster', 'arm_controller',
                 "'--controller-manager-timeout', '30'", 'use_sim_time',
                 'ros_gz_bridge', 'gz_sim.launch.py'):
        assert text in SOURCE
