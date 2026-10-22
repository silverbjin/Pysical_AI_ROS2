"""Break: opt-in native launch silently falls back to legacy hip/sensor model."""
import importlib.util
from pathlib import Path

import pytest
from launch import LaunchContext
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters

from integrated_robot_navigation import scene
from integrated_robot_navigation.geometry import description_dir


def launch_module(engine):
    file = description_dir() / 'launch' / (engine+'.launch.py')
    spec = importlib.util.spec_from_file_location('navigation_'+engine, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('engine', ['mujoco', 'gazebo'])
def test_navigation_launch_uses_exact_scene_urdf(tmp_path, monkeypatch, engine):
    record = scene.materialize_scene(engine, 'g1', tmp_path/'scene')
    module = launch_module(engine)
    original = module.get_package_share_directory
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name:
                        str(description_dir()) if name == 'integrated_robot_description' else original(name))
    if engine == 'mujoco':
        monkeypatch.setattr(module, 'probe_snapshot_plugin', lambda path: {})
    ctx = LaunchContext()
    config = Path(__file__).resolve().parents[1]/'config'
    ctx.launch_configurations.update(dict(
        vision_enabled='true', vision_camera_backend='snapshot', mujoco_headless='true',
        world='', model_path='', navigation_enabled='true', navigation_scene=str(tmp_path/'scene'),
        navigation_plugins=str(config/'mujoco_navigation_plugins.yaml'),
        navigation_bridge=str(config/'navigation_bridge.yaml')))
    parameters = [p for action in module.launch_nodes(ctx) if isinstance(action, Node)
                  for p in evaluate_parameters(ctx, action._Node__parameters) if isinstance(p, dict)]
    descriptions = [p['robot_description'] for p in parameters if 'robot_description' in p]
    assert descriptions and all(value == Path(record['robot']['path']).read_text() for value in descriptions)


def test_scene_loader_rejects_changed_bound_model(tmp_path):
    record = scene.materialize_scene('mujoco', 'g1', tmp_path/'scene')
    assert hasattr(scene, 'load_scene'), 'launch scene binding missing'
    assert scene.load_scene('mujoco', tmp_path/'scene')['robot'] == record['robot']
    Path(record['robot']['path']).write_text('<robot name="unexpected"/>')
    with pytest.raises(ValueError, match='hash'):
        scene.load_scene('mujoco', tmp_path/'scene')
