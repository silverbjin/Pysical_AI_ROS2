"""Validate RViz-only launch wiring and Ch05 display contract."""
import ast
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_launch_parses_and_sets_clock_parameter():
    source = (ROOT / 'launch/rviz_only.launch.py').read_text()
    compile(ast.parse(source), 'rviz_only.launch.py', 'exec')
    assert 'use_sim_time' in source
    assert 'manipulation.rviz' in source
    assert 'ParameterValue' in source


def test_config_robot_and_tf_topics():
    config = yaml.safe_load((ROOT / 'rviz/manipulation.rviz').read_text())
    manager = config['Visualization Manager']
    assert manager['Global Options']['Fixed Frame'] == 'world'
    displays = manager['Displays']
    classes = {v['Class'] for v in displays}
    assert 'rviz_default_plugins/RobotModel' in classes
    assert 'rviz_default_plugins/TF' in classes
    robot = next(v for v in displays if v['Class'].endswith('/RobotModel'))
    assert robot['Description Topic']['Value'] == '/robot_description'
    assert robot['Description Topic']['Durability Policy'] == 'Transient Local'
