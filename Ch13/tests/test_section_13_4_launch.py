"""Build real launch entities and validate inputs without starting a second engine."""
import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
import pytest
import yaml

SRC = Path(__file__).resolve().parents[1]/'ros2_ws/src'


def load(package, name):
    spec = importlib.util.spec_from_file_location(name, SRC/package/'launch'/name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context(**overrides):
    ctx = LaunchContext()
    ctx.launch_configurations.update(dict(engine='mujoco', detector_backend='color_fixture',
        weights_path='', processing_delay_s='0', use_sim_time='true', tracking_enabled='false',
        world='', model_path='', allow_camera_motion_test='false'))
    ctx.launch_configurations.update(overrides)
    return ctx


def test_observation_launch_contains_two_nodes_and_requires_explicit_backend_assets():
    module = load('integrated_robot_vision', 'vision.launch.py')
    nodes = module.launch_nodes(context())
    assert len(nodes) == 2 and all(isinstance(v, Node) for v in nodes)
    with pytest.raises(ValueError):
        module.launch_nodes(context(detector_backend='unknown'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(detector_backend='yolo', weights_path='yolov8n.pt'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(processing_delay_s='nan'))


def test_system_launch_includes_one_engine_runtime_and_vision_default_observation_only():
    module = load('integrated_robot_runtime', 'vision_system.launch.py')
    actions = module.launch_nodes(context())
    assert len(actions) == 3 and all(isinstance(v, IncludeLaunchDescription) for v in actions)
    requested = module.launch_nodes(context(tracking_enabled='true'))
    assert len(requested) == 4 and isinstance(requested[-1], Node)
    with pytest.raises(ValueError):
        module.launch_nodes(context(engine='both'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(use_sim_time='false'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(detector_backend='yolo', weights_path='/missing/weights.pt'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(processing_delay_s='nan'))
    with pytest.raises(ValueError):
        module.launch_nodes(context(allow_camera_motion_test='maybe'))


def test_legacy_mujoco_explicit_camera_config_keeps_eye_disabled():
    module = load('integrated_robot_description', 'mujoco.launch.py')
    share = SRC/'integrated_robot_description'
    config = module.camera_plugin_config(share, vision=False)
    plugins = yaml.safe_load(Path(config).read_text())['/**']['ros__parameters']['mujoco_plugins']
    camera, = plugins.values()
    assert camera['overview']['policy'] == 'streaming'
    assert camera['eye_in_hand']['policy'] == 'disabled'
    merged = yaml.safe_load(Path(module.materialize_controller_config(
        share/'config/controllers.yaml', config)).read_text())
    assert merged['controller_manager']['ros__parameters']['update_rate'] == 100
