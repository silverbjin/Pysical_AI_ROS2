"""Actual short-lived child processes exercise failure/owned-cleanup paths."""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0, str(SCRIPTS))


def test_timeout_records_the_specific_failed_stage_and_last_inputs():
    runner = importlib.import_module('run_vision_13_4')
    stages = []
    with pytest.raises(TimeoutError, match='tracking_ack'):
        runner.wait_for_stage(lambda: False, lambda: None, .01,
            stage='tracking_ack', stages=stages, snapshot=lambda: dict(goal_count=1))
    assert stages[-1]['status'] == 'TIMEOUT'
    assert stages[-1]['stage'] == 'tracking_ack'
    assert stages[-1]['last_inputs'] == {'goal_count': 1}


def test_successful_stage_is_recorded_without_an_extra_callback_step():
    runner = importlib.import_module('run_vision_13_4')
    stages = []
    runner.wait_for_stage(lambda: True, lambda: pytest.fail('unnecessary callback'), .1,
                          stage='already_ready', stages=stages)
    assert stages[-1]['status'] == 'PASS'


def test_cup_recognition_does_not_pass_from_a_detected_background_table():
    runner = importlib.import_module('run_vision_13_4')
    table = dict(boxes=[dict(class_id='60')])
    result = runner.recognition_summary([table]*12, [dict(valid=True, class_id='60')]*6, '41')
    assert result['frames'] == 12
    assert result['detected_frames'] == 0 and result['valid_3d'] == 0
    cup = dict(boxes=[dict(class_id='41')])
    result = runner.recognition_summary([cup]*12, [dict(valid=True, class_id='41')]*6, '41')
    assert result['detected_frames'] == 12 and result['valid_3d'] == 6


def test_observer_preserves_diagnostic_timeline_not_only_aggregate_counts():
    observer = importlib.import_module('vision_observer_13_4')
    from std_msgs.msg import String
    from collections import Counter
    state = SimpleNamespace(invalid=Counter(), diagnostics=[])
    observer.VisionObserver.on_status(state, String(data=json.dumps(dict(
        status='TF_UNAVAILABLE', capture_ns=1234, detail='future extrapolation'))))
    assert state.invalid['TF_UNAVAILABLE'] == 1
    assert state.diagnostics[-1]['capture_ns'] == 1234
    assert state.diagnostics[-1]['detail'] == 'future extrapolation'
    assert state.diagnostics[-1]['wall'] > 0


def test_observer_keeps_leg_readiness_timeline_for_standing_gate_diagnosis():
    observer = importlib.import_module('vision_observer_13_4')
    from std_msgs.msg import String
    state = SimpleNamespace(legs={}, leg_states=[])
    observer.VisionObserver.on_legs(state, String(data=json.dumps(dict(
        active=True, ready=False, mode='STOP', max_timer_gap_s=.62))))
    assert state.leg_states[-1]['ready'] is False
    assert state.leg_states[-1]['wall'] > 0
    assert state.leg_states[-1]['max_timer_gap_s'] == .62


def test_offset_fixture_changes_physical_geometry_not_sensor_or_command_source(tmp_path):
    runner = importlib.import_module('run_vision_13_4')
    import xml.etree.ElementTree as ET
    share = Path(__file__).resolve().parents[1]/'ros2_ws/src/integrated_robot_description'
    for engine in ('mujoco', 'gazebo'):
        path = runner.offset_fixture(engine, share, tmp_path, .02)
        tree = ET.parse(path)
        if engine == 'mujoco':
            assert tree.find('.//geom').get('pos') == '1 0.02 .72'
            assert Path(tree.find('include').get('file')).is_absolute()
        else:
            assert tree.find('.//model[@name="vision_fixture"]/pose').text == '1 0.02 .72 0 0 0'
        assert (share/('mujoco/vision_fixture.xml' if engine == 'mujoco' else 'worlds/vision_fixture.sdf')).is_file()
    assert 'input_loss_stop' in runner.required_checks('safety')
    assert 'five_second_tracking' not in runner.required_checks('safety')
    assert 'input_loss_stop' not in runner.required_checks('tracking')


def test_observer_preserves_full_calibration_and_measured_velocity(tmp_path):
    from sensor_msgs.msg import CameraInfo, JointState
    from rclpy.time import Time
    observer = importlib.import_module('vision_observer_13_4')
    state = SimpleNamespace(counts=__import__('collections').Counter(), latest_images={},
        cache=__import__('integrated_robot_vision.cache', fromlist=['RGBDCache']).RGBDCache(),
        invalid=__import__('collections').Counter(), calibrations={}, joints=[], joint_velocities=[])
    info = CameraInfo(width=320, height=240, distortion_model='plumb_bob')
    info.header.frame_id = 'camera_optical_frame'
    info.header.stamp = Time(seconds=1.).to_msg()
    info.k = [277., 0., 160., 0., 277., 120., 0., 0., 1.]
    info.r = [1., 0., 0., 0., 1., 0., 0., 0., 1.]
    observer.VisionObserver.on_info(state, info)
    assert state.calibrations[1.]['k'] == list(info.k)
    assert state.calibrations[1.]['r'] == list(info.r)
    assert 'roi' in state.calibrations[1.]
    names = list(observer.ARM_NAMES)+list(observer.LEG_NAMES)
    msg = JointState(name=names, position=[0.]*18, velocity=[.01]*18)
    observer.VisionObserver.on_joints(state, msg)
    assert state.joint_velocities[-1] == [.01]*6


def test_unprocessed_native_snapshot_never_claims_a_detection():
    observer = importlib.import_module('vision_observer_13_4')
    from sensor_msgs.msg import Image
    image = Image()
    seen = []
    bundle = object()
    state = SimpleNamespace(cache=SimpleNamespace(rgb={1.: (image, 0.)},
        match=lambda stamp, frame, epoch: bundle),
        save_frame=lambda value, box, **kw: seen.append((value, box, kw)))
    assert observer.VisionObserver.save_latest_frame(state)
    assert seen == [(bundle, None, {'empty_label': 'No published inference result'})]


def test_missing_weights_replaces_old_pass_before_any_engine_launch(tmp_path):
    (tmp_path/'result.json').write_text(json.dumps(dict(status='PASS', run_id='old')))
    process = subprocess.run([sys.executable, str(SCRIPTS/'run_vision_13_4.py'),
        '--engine', 'mujoco', '--detector-backend', 'yolo', '--weights-path', '/missing/weights.pt',
        '--scenario', 'yolo', '--output-dir', str(tmp_path)], capture_output=True, text=True, timeout=8.)
    assert process.returncode != 0
    result = json.loads((tmp_path/'result.json').read_text())
    assert result['run_id'] != 'old' and result['status'] == 'FAIL'
    assert not result.get('processes', [])


def test_child_death_fails_and_cleanup_never_signals_an_unrelated_group(tmp_path):
    runner = importlib.import_module('run_vision_13_4')
    unrelated = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'],
                                 start_new_session=True)
    try:
        args = argparse.Namespace(engine='mujoco', detector_backend='color_fixture', weights_path='',
            scenario='static', output_dir=str(tmp_path), timeout=1., duration=1., processing_delay_s=None)
        result = runner.run_trial(args, launch_command=[sys.executable, '-c', 'raise SystemExit(7)'])
        assert result['status'] == 'FAIL'
        assert result['cleanup'] and not result['cleanup'][0]['residual_live_pids']
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=3.)


def test_fixture_launch_omits_empty_optional_weights_instead_of_invalid_ros_argument():
    runner = importlib.import_module('run_vision_13_4')
    args = argparse.Namespace(engine='mujoco', detector_backend='color_fixture',
                              weights_path='', scenario='static')
    command = runner.build_launch_command(args, 0.)
    assert not any(value.endswith(':=') for value in command)
    assert 'weights_path:=' not in command
    args.weights_path = '/explicit/weights.pt'
    assert 'weights_path:=/explicit/weights.pt' in runner.build_launch_command(args, .15)


def test_comparison_rate_reaches_launch_and_invalid_rate_never_starts_engine():
    runner = importlib.import_module('run_vision_13_4')
    args = argparse.Namespace(engine='mujoco', detector_backend='color_fixture',
                              weights_path='', scenario='tracking')
    assert 'max_rate_hz:=10.0' in runner.build_launch_command(args, 0.)
    args.inference_rate_hz = 15.
    assert 'max_rate_hz:=15.0' in runner.build_launch_command(args, 0.)
    for value in (15.01, float('nan'), 0.):
        args.inference_rate_hz = value
        with pytest.raises(ValueError):
            runner.build_launch_command(args, 0.)


def test_snapshot_backend_reaches_only_mujoco_launch_and_invalid_choice_is_rejected():
    runner = importlib.import_module('run_vision_13_4')
    args = argparse.Namespace(engine='mujoco', detector_backend='color_fixture',
        weights_path='', scenario='tracking', vision_camera_backend='snapshot')
    assert 'vision_camera_backend:=snapshot' in runner.build_launch_command(args, 0.)
    args.engine = 'gazebo'
    assert not any(v.startswith('vision_camera_backend:=') for v in runner.build_launch_command(args, 0.))
    args.vision_camera_backend = 'typo'
    with pytest.raises(ValueError):
        runner.build_launch_command(args, 0.)


def test_snapshot_camera_ownership_rejects_a_duplicate_or_missing_sensor_writer():
    runner = importlib.import_module('run_vision_13_4')
    topics = ('/camera/color/image_raw', '/camera/aligned_depth_to_color/image_raw',
              '/native/camera_info', '/camera/color/camera_info')
    owners = {topic: ['one_sensor_writer'] for topic in topics}
    assert runner.camera_publishers_unique(owners)
    owners[topics[0]].append('second_eye_plugin')
    assert not runner.camera_publishers_unique(owners)
    owners[topics[0]] = []
    assert not runner.camera_publishers_unique(owners)
    assert 'single_camera_owners' in runner.required_checks('static', engine='mujoco', camera_backend='snapshot')


@pytest.mark.parametrize('topic', ['/overview/color', '/overview/depth',
    '/overview/camera_info', '/eye_in_hand/color', '/eye_in_hand/depth',
    '/eye_in_hand/camera_info'])
def test_snapshot_ownership_rejects_hidden_auto_registered_camera(topic):
    runner = importlib.import_module('run_vision_13_4')
    owners = {name: ['one_writer'] for name in (
        '/camera/color/image_raw', '/camera/aligned_depth_to_color/image_raw',
        '/native/camera_info', '/camera/color/camera_info')}
    owners[topic] = ['legacy_auto_camera']
    assert not runner.camera_publishers_unique(owners)


def test_read_only_library_audit_uses_real_owned_mapping_and_rejects_unrelated_pid(tmp_path):
    import os
    from ament_index_python.packages import get_package_prefix
    runner = importlib.import_module('run_vision_13_4')
    prefix = Path(get_package_prefix('integrated_robot_camera'))
    library = prefix/'lib/libsnapshot_camera_plugin.so'
    code = 'import ctypes,signal; ctypes.CDLL('+repr(str(library))+'); print("loaded",flush=True); signal.pause()'
    own = subprocess.Popen([sys.executable, '-c', code], start_new_session=True,
                           stdout=subprocess.PIPE, text=True)
    other = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'], start_new_session=True)
    try:
        assert own.stdout.readline().strip() == 'loaded'
        loaded = runner.mapped_camera_library(own.pid, own.pid, library)
        assert loaded['library_path'] == str(library.resolve())
        assert len(loaded['library_sha256']) == 64
        assert loaded['mailbox_library_path'] == str((prefix/'lib/libsnapshot_mailbox.so').resolve())
        assert len(loaded['mailbox_library_sha256']) == 64
        with pytest.raises(ValueError, match='unrelated'):
            runner.mapped_camera_library(other.pid, own.pid, library)
        # A Python loader is not the native MuJoCo control process, even with the .so mapped.
        own.ch13_system_log = tmp_path/'system.log'
        own.ch13_system_log.write_text('integrated_robot_camera/SnapshotCameraPlugin initialized\n')
        with pytest.raises(RuntimeError, match='native'):
            runner.audit_camera_backend(own, prefix)
        assert other.poll() is None and os.getpgid(other.pid) != own.pid
    finally:
        for child in (own, other):
            child.terminate()
            child.wait(timeout=3.)


def test_jazzy_dict_message_info_records_actual_tf_publisher_identity():
    observer = importlib.import_module('vision_observer_13_4')
    state = SimpleNamespace(tf_owners={}, tf_parents={}, tf_metadata_fields=set())
    message = SimpleNamespace(transforms=[SimpleNamespace(child_frame_id='base_footprint',
                              header=SimpleNamespace(frame_id='odom'))])
    observer.VisionObserver.on_tf(state, message, {'publisher_gid': bytes(range(16))})
    assert state.tf_owners == {'base_footprint': {bytes(range(16)).hex()}}
    with pytest.raises(ValueError):
        observer.VisionObserver.on_tf(state, message, {})


def test_jazzy_without_gid_records_parents_but_requires_graph_and_model_ownership_contract():
    observer = importlib.import_module('vision_observer_13_4')
    state = SimpleNamespace(tf_owners={}, tf_parents={}, tf_metadata_fields=set())
    message = SimpleNamespace(transforms=[SimpleNamespace(child_frame_id='base_footprint',
                              header=SimpleNamespace(frame_id='odom'))])
    observer.VisionObserver.on_tf(state, message, dict(source_timestamp=1, received_timestamp=2))
    assert state.tf_parents == {'base_footprint': {'odom'}}
    assert state.tf_owners == {}  # do not fabricate a publisher GID
    verifier = importlib.import_module('verify_vision_13_4')
    graph = {'/tf': ['native_pose_adapter', 'robot_state_publisher'],
             '/tf_static': ['robot_state_publisher']}
    assert verifier.tf_contract_single_owners(graph, state.tf_parents, {'base_footprint': 'odom'})
    graph['/tf'].append('unknown_duplicate_source')
    assert not verifier.tf_contract_single_owners(graph, state.tf_parents, {'base_footprint': 'odom'})


def test_native_stop_wait_is_bounded_and_only_accepts_owned_process_group_members():
    runner = importlib.import_module('run_vision_13_4')
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(.2)'],
                               start_new_session=True)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(5)'],
                                 start_new_session=True)
    try:
        with pytest.raises(ValueError):
            runner.wait_owned_members_exit(process, [unrelated.pid], timeout=.05)
        assert runner.wait_owned_members_exit(process, [process.pid], timeout=2.)
        assert unrelated.poll() is None
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=3.)
        unrelated.terminate()
        unrelated.wait(timeout=3.)


def test_stack_capture_refuses_unrelated_process_before_launching_debugger(tmp_path):
    runner = importlib.import_module('run_vision_13_4')
    own = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'], start_new_session=True)
    other = subprocess.Popen([sys.executable, '-c', 'import signal; signal.pause()'], start_new_session=True)
    try:
        with pytest.raises(ValueError, match='unrelated'):
            runner.snapshot_owned_stacks(own, [other.pid], tmp_path)
        assert other.poll() is None and not list(tmp_path.iterdir())
    finally:
        for child in (own, other):
            child.terminate()
            child.wait(timeout=3.)


def test_gazebo_ruby_setproctitle_is_recognized_without_selecting_shell_wrapper():
    runner = importlib.import_module('run_vision_13_4')
    assert runner.is_gazebo_command(b'gz sim -r -s --headless-rendering /world.sdf\0\0\0')
    assert runner.is_gazebo_command(b'ruby\0/opt/bin/gz\0sim\0-r\0-s\0')
    assert not runner.is_gazebo_command(b'/bin/sh\0-c\0ruby /opt/bin/gz sim -s\0')
    assert not runner.is_gazebo_command(b'python\0observer.py\0')


def test_launch_internal_child_sigkill_is_not_clean_even_if_parent_exits_zero():
    runner = importlib.import_module('run_vision_13_4')
    cleanup = [dict(forced_cleanup=False, residual_live_pids=[])]
    assert runner.clean_shutdown(cleanup, 0, 'all own children finished cleanly')
    assert not runner.clean_shutdown(cleanup, 0, "process failed to terminate, escalating to 'SIGKILL'")
    assert not runner.clean_shutdown(cleanup, 0, 'process has died [exit code -9]')
    assert not runner.clean_shutdown(cleanup, 1, '')
