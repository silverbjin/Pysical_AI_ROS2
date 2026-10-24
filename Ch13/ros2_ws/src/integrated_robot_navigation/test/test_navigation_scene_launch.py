"""Break: opt-in native launch silently falls back to legacy hip/sensor model."""
import importlib.util
import json
from pathlib import Path

import pytest
from launch import LaunchContext
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.utilities import perform_substitutions
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


def test_navigation_gazebo_launch_owns_engine_pid_not_shell_wrapper(tmp_path, monkeypatch):
    record = scene.materialize_scene('gazebo', 'g1', tmp_path/'scene with spaces')
    module = launch_module('gazebo')
    original = module.get_package_share_directory
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name:
        str(description_dir()) if name == 'integrated_robot_description' else original(name))
    ctx = LaunchContext()
    ctx.launch_configurations.update(dict(vision_enabled='true', navigation_enabled='true',
        navigation_scene=str(tmp_path/'scene with spaces'), world='',
        navigation_bridge=str(Path(__file__).resolve().parents[1]/'config/navigation_bridge.yaml')))
    actions = module.launch_nodes(ctx)
    native = [action for action in actions if isinstance(action, ExecuteProcess)
              and not isinstance(action, Node)]
    assert len(native) == 1, 'native engine must be a direct launch child, not an included shell'
    executable = native[0].process_description
    assert native[0].shell is False
    command = [perform_substitutions(ctx, part) for part in executable.cmd]
    assert Path(command[0]).name.startswith('ruby')
    assert Path(command[1]).name == 'gz' and command[2:5] == ['sim', '-r', '-s']
    assert '--headless-rendering' in command
    assert command.count(record['world']['path']) == 1  # one argv, even with spaces
    index = command.index('--force-version')
    assert command[index+1] == '8'


def test_legacy_gazebo_keeps_the_upstream_launch_path(monkeypatch):
    module = launch_module('gazebo')
    original = module.get_package_share_directory
    monkeypatch.setattr(module, 'get_package_share_directory', lambda name:
        str(description_dir()) if name == 'integrated_robot_description' else original(name))
    ctx = LaunchContext()
    ctx.launch_configurations.update(dict(vision_enabled='true', navigation_enabled='false', world=''))
    actions = module.launch_nodes(ctx)
    assert len([action for action in actions if isinstance(action, IncludeLaunchDescription)]) == 1
    assert not [action for action in actions if isinstance(action, ExecuteProcess)
                and not isinstance(action, Node)]


def test_scene_loader_rejects_changed_bound_model(tmp_path):
    record = scene.materialize_scene('mujoco', 'g1', tmp_path/'scene')
    assert hasattr(scene, 'load_scene'), 'launch scene binding missing'
    assert scene.load_scene('mujoco', tmp_path/'scene')['robot'] == record['robot']
    Path(record['robot']['path']).write_text('<robot name="unexpected"/>')
    with pytest.raises(ValueError, match='hash'):
        scene.load_scene('mujoco', tmp_path/'scene')


def test_scene_loader_restores_missing_verified_native_cache_only(tmp_path, monkeypatch):
    native_tmp = tmp_path/'native-tmp'
    native_tmp.mkdir()
    monkeypatch.setattr(scene.tempfile, 'gettempdir', lambda: str(native_tmp))
    record = scene.materialize_scene('mujoco', 'g1', tmp_path/'scene')
    cache = Path(record['native_controllers']['path'])
    expected = cache.read_bytes()
    cache.unlink()  # only this test's generated file; persistent bundle is intact
    loaded = scene.load_scene('mujoco', tmp_path/'scene')
    assert loaded['native_controllers'] == record['native_controllers']
    assert loaded['controllers'] == record['controllers']
    assert cache.read_bytes() == expected
    cache.write_bytes(b'corrupt preexisting cache')
    with pytest.raises(ValueError, match='hash'):
        scene.load_scene('mujoco', tmp_path/'scene')
    assert cache.read_bytes() == b'corrupt preexisting cache'


def test_scene_loader_never_reconstructs_cache_from_tampered_source(tmp_path, monkeypatch):
    native_tmp = tmp_path/'native-tmp'
    native_tmp.mkdir()
    monkeypatch.setattr(scene.tempfile, 'gettempdir', lambda: str(native_tmp))
    record = scene.materialize_scene('mujoco', 'g1', tmp_path/'scene')
    cache = Path(record['native_controllers']['path'])
    cache.unlink()
    Path(record['controllers']['path']).write_bytes(b'tampered persistent source')
    with pytest.raises(ValueError, match='hash'):
        scene.load_scene('mujoco', tmp_path/'scene')
    assert not cache.exists()


def test_scene_loader_rejects_unowned_native_cache_target(tmp_path, monkeypatch):
    native_tmp = tmp_path/'native-tmp'
    native_tmp.mkdir()
    monkeypatch.setattr(scene.tempfile, 'gettempdir', lambda: str(native_tmp))
    record = scene.materialize_scene('mujoco', 'g1', tmp_path/'scene')
    foreign = tmp_path/'unrelated.yaml'
    record['native_controllers']['path'] = str(foreign)
    (tmp_path/'scene/scene.json').write_text(json.dumps(record))
    with pytest.raises(ValueError, match='native controller.*path'):
        scene.load_scene('mujoco', tmp_path/'scene')
    assert not foreign.exists()
