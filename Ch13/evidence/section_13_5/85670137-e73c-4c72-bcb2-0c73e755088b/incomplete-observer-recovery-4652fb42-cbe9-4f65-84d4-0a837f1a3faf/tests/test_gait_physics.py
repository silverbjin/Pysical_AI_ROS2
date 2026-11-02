"""Break: ideal-feedback tests hide load error and real foot sliding in STAND."""
from pathlib import Path
import json
import mujoco
from integrated_robot_navigation.scene import materialize_scene
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.carry_profile import default_limits
from native_physics_fixture import stand_probe, calibration_probe


def test_actual_actuator_stand_holds_feet_and_tracks_without_root_writes(tmp_path):
    scene = materialize_scene('mujoco', 'g1', tmp_path/'physics-component')
    model = compile_model(Path(scene['robot']['path']).read_text())
    native = mujoco.MjModel.from_xml_path(scene['world']['path'])
    data = mujoco.MjData(native)
    mujoco.mj_resetDataKeyframe(native, data, 0)
    for name in model.limits:
        actuator = native.actuator(name+'_motor').id
        effort = model.limits[name][3]
        assert native.actuator_forcelimited[actuator]
        assert max(abs(value) for value in native.actuator_forcerange[actuator]) <= effort
    report = stand_probe(native, data, model, default_limits())
    assert report['state'] == 'STAND' and report['duration_s'] >= 5., report
    assert report['maximum_native_foot_motion_m'] <= .02, report
    assert report['maximum_joint_error_rad'] <= .03, report


def test_actual_carry_survives_contact_calibration_without_root_writes(tmp_path):
    scene = materialize_scene('mujoco', 'g1', tmp_path/'calibration-component')
    model = compile_model(Path(scene['robot']['path']).read_text())
    native = mujoco.MjModel.from_xml_path(scene['world']['path'])
    data = mujoco.MjData(native)
    mujoco.mj_resetDataKeyframe(native, data, 0)
    report = calibration_probe(native, data, model, default_limits())
    assert report['completed'], json.dumps(report, indent=2)
    assert report['maximum_carry_error_rad'] <= .03, report
    assert report['maximum_carry_velocity_rps'] <= .02, report
    assert report['maximum_gripper_error_m'] <= .002, report
    assert report['maximum_gripper_velocity_mps'] <= .005, report
