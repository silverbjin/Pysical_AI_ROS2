from pathlib import Path
import math
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "ros2_ws/src/integrated_robot_description"
XACRO = PKG / "urdf/robot_system.urdf.xacro"
CONTROLLERS = PKG / "config/controllers.yaml"

LEG_JOINTS = tuple(
    f"{leg}_{joint}_joint"
    for leg in ("fr", "fl", "rr", "rl")
    for joint in ("hip", "thigh", "calf")
)
ARM_JOINTS = tuple(f"arm_joint_{index}" for index in range(1, 7))
GRIPPER_JOINTS = ("gripper_left_joint", "gripper_right_joint")
MOVABLE_JOINTS = LEG_JOINTS + ARM_JOINTS + GRIPPER_JOINTS


def expand(backend: str) -> ET.Element:
    result = subprocess.run(
        ["xacro", str(XACRO), f"control_backend:={backend}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return ET.fromstring(result.stdout)


def test_model_contract_has_exactly_20_prefixed_movable_joints():
    root = expand("mock")
    movable = tuple(
        joint.attrib["name"]
        for joint in root.findall("joint")
        if joint.attrib["type"] != "fixed"
    )
    assert set(movable) == set(MOVABLE_JOINTS)
    assert len(movable) == len(set(movable)) == 20
    assert all(name.startswith("arm_") for name in ARM_JOINTS)
    arm_links = [link.attrib["name"] for link in root.findall("link") if "arm" in link.attrib["name"]]
    assert arm_links
    assert all(name.startswith("arm_") for name in arm_links)


def test_model_is_one_tree_with_positive_inertia():
    root = expand("mock")
    links = {link.attrib["name"] for link in root.findall("link")}
    children = [joint.find("child").attrib["link"] for joint in root.findall("joint")]
    assert len(links - set(children)) == 1
    assert links - set(children) == {"base_footprint"}
    assert len(children) == len(set(children))
    assert {"base_link", "lidar_link", "arm_mount", "arm_base_link", "arm_tool0", "camera_link"} <= links

    parents = {
        joint.find("child").attrib["link"]: joint.find("parent").attrib["link"]
        for joint in root.findall("joint")
    }
    assert parents["lidar_link"] == "base_link"
    assert parents["arm_mount"] == "base_link"
    assert parents["camera_link"] == "arm_link_6"

    for link in root.findall("link"):
        inertial = link.find("inertial")
        assert inertial is not None, link.attrib["name"]
        mass = float(inertial.find("mass").attrib["value"])
        inertia = inertial.find("inertia").attrib
        assert math.isfinite(mass) and mass > 0
        assert all(math.isfinite(float(inertia[key])) and float(inertia[key]) > 0 for key in ("ixx", "iyy", "izz"))


@pytest.mark.parametrize(
    ("backend", "plugin"),
    [
        ("mock", "mock_components/GenericSystem"),
        ("gazebo", "gz_ros2_control/GazeboSimSystem"),
        ("mujoco", "mujoco_ros2_control/MujocoSystemInterface"),
    ],
)
def test_backend_selects_one_hardware_plugin(backend, plugin):
    root = expand(backend)
    blocks = root.findall("ros2_control")
    assert len(blocks) == 1
    plugins = [element.text.strip() for element in blocks[0].findall("./hardware/plugin")]
    assert plugins == [plugin]
    declared = {joint.attrib["name"] for joint in blocks[0].findall("joint")}
    assert declared == set(MOVABLE_JOINTS)
    for joint in blocks[0].findall("joint"):
        assert [item.attrib["name"] for item in joint.findall("command_interface")] == ["position"]
        assert [item.attrib["name"] for item in joint.findall("state_interface")] == ["position", "velocity"]
        model_joint = root.find(f"joint[@name='{joint.attrib['name']}']")
        model_limit = model_joint.find("limit").attrib
        command_params = {
            item.attrib["name"]: item.text
            for item in joint.find("command_interface").findall("param")
        }
        assert float(command_params["min"]) == pytest.approx(float(model_limit["lower"]))
        assert float(command_params["max"]) == pytest.approx(float(model_limit["upper"]))


def test_controller_command_ownership_is_complete_and_disjoint():
    config = yaml.safe_load(CONTROLLERS.read_text(encoding="utf-8"))
    manager = config["controller_manager"]["ros__parameters"]
    expected_types = {
        "joint_state_broadcaster": "joint_state_broadcaster/JointStateBroadcaster",
        "leg_position_controller": "forward_command_controller/ForwardCommandController",
        "arm_trajectory_controller": "joint_trajectory_controller/JointTrajectoryController",
        "gripper_position_controller": "forward_command_controller/ForwardCommandController",
    }
    assert {name: manager[name]["type"] for name in expected_types} == expected_types

    owners = {
        "leg": tuple(config["leg_position_controller"]["ros__parameters"]["joints"]),
        "arm": tuple(config["arm_trajectory_controller"]["ros__parameters"]["joints"]),
        "gripper": tuple(config["gripper_position_controller"]["ros__parameters"]["joints"]),
    }
    assert owners == {"leg": LEG_JOINTS, "arm": ARM_JOINTS, "gripper": GRIPPER_JOINTS}
    flattened = sum(owners.values(), ())
    assert len(flattened) == len(set(flattened)) == 20
    assert set(flattened) == set(MOVABLE_JOINTS)

