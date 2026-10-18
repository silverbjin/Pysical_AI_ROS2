from pathlib import Path
import ast
import math
import subprocess
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "ros2_ws/src/integrated_robot_description"
MODEL = PKG / "mujoco/robot_system.xml"
LEG_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("fr", "fl", "rr", "rl")
    for joint in ("hip", "thigh", "calf")
)
ARM_JOINTS = tuple(f"arm_joint_{index}" for index in range(1, 7))
GRIPPER_JOINTS = ("gripper_left_joint", "gripper_right_joint")
EXPECTED = LEG_JOINTS + ARM_JOINTS + GRIPPER_JOINTS


def test_mjcf_has_exactly_20_named_position_actuators():
    root = ET.parse(MODEL).getroot()
    joints = {
        joint.attrib["name"]
        for joint in root.findall("./worldbody//joint")
        if joint.attrib.get("name") != "root"
    }
    actuators = root.findall("./actuator/position")
    assert joints == set(EXPECTED)
    assert len(actuators) == 20
    assert {actuator.attrib["joint"] for actuator in actuators} == set(EXPECTED)
    assert all(actuator.attrib["name"] == f"{actuator.attrib['joint']}_motor" for actuator in actuators)


def test_mjcf_joint_axes_and_limits_match_expanded_urdf():
    urdf_text = subprocess.run(
        ["xacro", str(PKG / "urdf/robot_system.urdf.xacro"), "control_backend:=mock"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    urdf = ET.fromstring(urdf_text)
    mjcf = ET.parse(MODEL).getroot()
    urdf_joints = {joint.attrib["name"]: joint for joint in urdf.findall("joint")}
    mjcf_joints = {joint.attrib["name"]: joint for joint in mjcf.findall("./worldbody//joint") if joint.attrib.get("name") != "root"}
    for name in EXPECTED:
        urdf_axis = tuple(float(value) for value in urdf_joints[name].find("axis").attrib["xyz"].split())
        mjcf_axis = tuple(float(value) for value in mjcf_joints[name].attrib["axis"].split())
        urdf_limit = urdf_joints[name].find("limit").attrib
        mjcf_limit = tuple(float(value) for value in mjcf_joints[name].attrib["range"].split())
        assert mjcf_axis == urdf_axis
        assert mjcf_limit == pytest.approx(
            (float(urdf_limit["lower"]), float(urdf_limit["upper"]))
        )

    bodies = {body.attrib.get("name") for body in mjcf.findall("./worldbody//body")}
    assert {"lidar_link", "camera_link"} <= bodies


def test_native_mujoco_loads_and_steps_finite_upright_model():
    model = mujoco.MjModel.from_xml_path(str(MODEL))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    for index in range(model.nu):
        data.ctrl[index] = model.key_ctrl[0, index]
    heights = []
    for _ in range(1500):
        mujoco.mj_step(model, data)
        heights.append(float(data.qpos[2]))
    assert model.nu == 20
    assert np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all()
    assert min(heights[-500:]) > 0.35
    rotation = data.xmat[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_link")].reshape(3, 3)
    assert math.acos(float(np.clip(rotation[2, 2], -1, 1))) < 0.15


def test_mujoco_launch_uses_official_system_interface_and_custom_node():
    source = (PKG / "launch/mujoco.launch.py").read_text(encoding="utf-8")
    ast.parse(source)
    assert "package='mujoco_ros2_control'" in source
    assert "executable='ros2_control_node'" in source
    assert "control_backend:=mujoco" in source
    assert "robot_system.xml" in source
    assert "'--param-file', controllers" in source
    assert "materialize_controller_config" in source
    assert "tempfile.gettempdir" in source


def test_mujoco_source_dependency_is_pinned_and_declared():
    repos = (ROOT / "ros2_ws/mujoco_ros2_control.repos").read_text(encoding="utf-8")
    package = (PKG / "package.xml").read_text(encoding="utf-8")
    assert "https://github.com/ros-controls/mujoco_ros2_control.git" in repos
    assert "c261f5552edf124d1000a23fb25b6c07cadeb807" in repos
    assert "<exec_depend>mujoco_ros2_control</exec_depend>" in package


def test_native_verifier_writes_measured_result():
    source = (ROOT / "scripts/verify_mujoco_13_2.py").read_text(encoding="utf-8")
    names = {node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}
    assert {"joint_names", "actuator_names", "run", "write_result"} <= names
    assert "mj_step" in source

