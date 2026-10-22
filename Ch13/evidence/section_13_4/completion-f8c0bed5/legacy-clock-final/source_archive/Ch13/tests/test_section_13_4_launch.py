"""Build real launch entities and validate inputs without starting a second engine."""
import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch_ros.utilities import evaluate_parameters
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
import pytest
import yaml
import subprocess
import xml.etree.ElementTree as ET

SRC = Path(__file__).resolve().parents[1]/'ros2_ws/src'


def test_headless_option_reaches_native_hardware_without_changing_joints():
    path = SRC/'integrated_robot_description/urdf/robot_system.urdf.xacro'
    for value in ('true', 'false'):
        xml = subprocess.check_output(['xacro', str(path), 'control_backend:=mujoco',
                                      'mujoco_headless:='+value], text=True)
        root = ET.fromstring(xml)
        assert root.find('./ros2_control/hardware/param[@name="headless"]').text == value
        assert len(root.findall('./ros2_control/joint')) == 20


@pytest.mark.parametrize('vision,backend,expected', [
    ('true', 'snapshot', 'false'), ('true', 'upstream', 'true'),
    ('false', 'snapshot', 'true'), ('false', 'upstream', 'true')])
def test_snapshot_launch_disables_legacy_camera_auto_registration(
        vision, backend, expected, monkeypatch):
    module = load('integrated_robot_description', 'mujoco.launch.py')
    monkeypatch.setattr(module, 'get_package_share_directory',
                        lambda name: str(SRC/'integrated_robot_description'))
    ctx = context(vision_enabled=vision, vision_camera_backend=backend,
                  mujoco_headless='true')
    node = module.launch_nodes(ctx)[0]
    parameters = evaluate_parameters(ctx, node._Node__parameters)
    description = next(p['robot_description'] for p in parameters
                       if isinstance(p, dict) and 'robot_description' in p)
    root = ET.fromstring(description)
    value = root.find('./ros2_control/hardware/param[@name="auto_register_cameras"]')
    assert value is not None and value.text == expected
    assert len(root.findall('./ros2_control/joint')) == 20


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


def test_trace_arguments_reach_only_requested_nodes():
    run = '424240ff-0bfe-4a4b-92d4-93f6a78d49b8'
    ctx = context(trace_enabled='true', trace_run_id=run, vision_camera_backend='snapshot')
    vision = load('integrated_robot_vision', 'vision.launch.py')
    for node in vision.launch_nodes(ctx):
        parameters = evaluate_parameters(ctx, node._Node__parameters)
        assert any(v.get('trace_enabled') is True and v.get('trace_run_id') == run
                   for v in parameters if isinstance(v, dict)), 'missing explicit trace parameters'
    system = load('integrated_robot_runtime', 'vision_system.launch.py')
    actions = system.launch_nodes(ctx)
    for action in actions:
        assert dict(action.launch_arguments)['trace_run_id'] == run
    gazebo = system.launch_nodes(context(engine='gazebo', trace_enabled='true', trace_run_id=run))
    assert 'trace_enabled' not in dict(gazebo[0].launch_arguments)
    for arguments in ({'trace_enabled': 'maybe'}, {'trace_enabled': 'true', 'trace_run_id': ''}):
        with pytest.raises(ValueError):
            system.launch_nodes(context(**arguments))
    architecture = load('integrated_robot_runtime', 'architecture.launch.py')
    nodes = [v for v in architecture.launch_nodes(ctx) if isinstance(v, Node)]
    for node in nodes:
        parameters = evaluate_parameters(ctx, node._Node__parameters)
        tracing = [v for v in parameters if isinstance(v, dict) and 'trace_enabled' in v]
        executable = perform_substitutions(ctx, normalize_to_list_of_substitutions(node.node_executable))
        assert bool(tracing) is (executable == 'manipulation_node')


def test_trace_config_is_snapshot_only_and_does_not_edit_source():
    module = load('integrated_robot_description', 'mujoco.launch.py')
    share = SRC/'integrated_robot_description'
    source = share/'config/controllers.yaml'
    run = '424240ff-0bfe-4a4b-92d4-93f6a78d49b8'
    for backend in ('snapshot', 'upstream'):
        plugin = Path(module.camera_plugin_config(share, True, backend))
        before = plugin.read_bytes()
        options = {'trace_enabled': True, 'trace_run_id': run}
        merged = yaml.safe_load(Path(module.materialize_controller_config(
            source, plugin, trace_options=options)).read_text())
        eye = merged['/**']['ros__parameters']['mujoco_plugins']['eye_camera']
        assert ('trace_run_id' in eye) is (backend == 'snapshot')
        if backend == 'snapshot':
            assert eye['trace_enabled'] is True and eye['trace_run_id'] == run
        assert plugin.read_bytes() == before


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


def test_rate_option_is_forwarded_and_rejected_before_starting_native_engine():
    vision = load('integrated_robot_vision', 'vision.launch.py')
    system = load('integrated_robot_runtime', 'vision_system.launch.py')
    node = vision.launch_nodes(context(max_rate_hz='15'))[0]
    assert any(parameters.get('max_rate_hz') == 15. for parameters in
               evaluate_parameters(context(max_rate_hz='15'), node._Node__parameters)
               if isinstance(parameters, dict))
    actions = system.launch_nodes(context(max_rate_hz='15'))
    arguments = dict(actions[2].launch_arguments)
    assert arguments['max_rate_hz'] == '15'
    for value in ('15.01', 'nan', '0'):
        for module in (vision, system):
            with pytest.raises(ValueError):
                module.launch_nodes(context(max_rate_hz=value))


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


def test_snapshot_backend_changes_only_camera_class():
    module = load('integrated_robot_description', 'mujoco.launch.py')
    share = SRC/'integrated_robot_description'
    def plugins(backend):
        path = module.camera_plugin_config(share, True, backend)
        return yaml.safe_load(Path(path).read_text())['/**']['ros__parameters']['mujoco_plugins']
    upstream, snapshot = plugins('upstream'), plugins('snapshot')
    assert snapshot['eye_camera']['type'] == 'integrated_robot_camera/SnapshotCameraPlugin'
    assert snapshot['native_pose'] == upstream['native_pose']
    assert snapshot['eye_camera'] == dict(upstream['eye_camera'],
                                        type='integrated_robot_camera/SnapshotCameraPlugin')
    for backend in ('upstream', 'snapshot'):
        assert module.camera_plugin_config(share, False, backend) == module.camera_plugin_config(share, False)
    with pytest.raises(ValueError):
        module.camera_plugin_config(share, True, 'typo')


def test_camera_backend_forwarded_only_to_mujoco_and_unknown_fails_before_include():
    module = load('integrated_robot_runtime', 'vision_system.launch.py')
    for engine in ('mujoco', 'gazebo'):
        actions = module.launch_nodes(context(engine=engine, vision_camera_backend='snapshot'))
        arguments = dict(actions[0].launch_arguments)
        if engine == 'mujoco':
            assert arguments['vision_camera_backend'] == 'snapshot'
        else:
            assert 'vision_camera_backend' not in arguments
    with pytest.raises(ValueError):
        module.launch_nodes(context(vision_camera_backend='typo'))


def test_actual_snapshot_probe_accepts_active_prefix_and_rejects_other_prefix(tmp_path):
    from ament_index_python.packages import get_package_prefix
    import hashlib
    module = load('integrated_robot_description', 'mujoco.launch.py')
    prefix = Path(get_package_prefix('integrated_robot_camera'))
    audit = module.probe_snapshot_plugin(prefix)
    library = Path(audit['library_path'])
    assert audit['class_id'] == 'integrated_robot_camera/SnapshotCameraPlugin'
    assert library.is_file() and library.is_relative_to(prefix.resolve())
    assert audit['library_sha256'] == hashlib.sha256(library.read_bytes()).hexdigest()
    assert audit['package_prefix'] == str(prefix.resolve())
    with pytest.raises(RuntimeError):
        module.probe_snapshot_plugin(tmp_path)


def test_missing_probe_and_library_fail_before_native_node(tmp_path, monkeypatch):
    module = load('integrated_robot_description', 'mujoco.launch.py')
    monkeypatch.setattr(module, 'get_package_prefix', lambda name: str(tmp_path))
    monkeypatch.setattr(module, 'get_package_share_directory',
                        lambda name: str(SRC/'integrated_robot_description'))
    monkeypatch.setattr(module, 'Node', lambda **kwargs: pytest.fail('native node created before failed probe'))
    ctx = context(vision_enabled='true', mujoco_headless='true', vision_camera_backend='snapshot')
    with pytest.raises(RuntimeError, match='probe'):
        module.launch_nodes(ctx)
    # Only a disposable local probe double changes; real installed libraries stay untouched.
    probe = tmp_path/'lib/integrated_robot_camera/camera_plugin_probe'
    probe.parent.mkdir(parents=True)
    probe.write_text('#!/bin/sh\nprintf "%s\\n" "'+str(tmp_path/'lib/missing.so')+'"\n')
    probe.chmod(0o755)
    with pytest.raises(RuntimeError, match='library'):
        module.launch_nodes(ctx)
