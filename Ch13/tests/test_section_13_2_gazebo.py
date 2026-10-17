from pathlib import Path
import ast
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "ros2_ws/src/integrated_robot_description"


def test_gazebo_world_has_ground_physics_and_required_systems():
    world = ET.parse(PKG / "worlds/empty.sdf").getroot().find("world")
    assert world is not None
    assert world.findtext("gravity") == "0 0 -9.81"
    assert float(world.findtext("physics/max_step_size")) <= 0.002
    assert float(world.findtext("physics/real_time_factor")) == 1.0
    plugins = {plugin.attrib["name"] for plugin in world.findall("plugin")}
    assert {
        "gz::sim::systems::Physics",
        "gz::sim::systems::UserCommands",
        "gz::sim::systems::SceneBroadcaster",
    } <= plugins
    assert world.find("model[@name='ground_plane']") is not None


def test_gazebo_launch_has_one_spawn_and_all_controller_spawners():
    path = PKG / "launch/gazebo.launch.py"
    ast.parse(path.read_text(encoding="utf-8"))
    source = path.read_text(encoding="utf-8")
    assert source.count('executable="create"') == 1
    assert 'control_backend:=gazebo' in source
    assert "gz_sim.launch.py" in source
    for controller in (
        "joint_state_broadcaster",
        "leg_position_controller",
        "arm_trajectory_controller",
        "gripper_position_controller",
    ):
        assert source.count(f'"{controller}"') == 1
    assert "TimerAction" in source
    assert "materialize_controller_config" in source
    assert "tempfile.gettempdir" in source


def test_verifier_checks_state_command_and_controller_ownership():
    source = (ROOT / "scripts/verify_gazebo_13_2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert {"collect_joint_state", "list_controllers", "send_arm_goal", "write_result"} <= names
    assert "arm_joint_2" in source
    assert "20" in source
    assert 'choices=("gazebo", "mujoco")' in source

