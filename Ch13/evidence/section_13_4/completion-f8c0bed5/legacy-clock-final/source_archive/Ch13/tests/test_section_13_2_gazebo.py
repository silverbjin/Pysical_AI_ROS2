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
    from launch import LaunchContext
    from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
    from launch_ros.actions import Node

    path = PKG / "launch/gazebo.launch.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    executables = [keyword.value.value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == 'Node' for keyword in node.keywords
                   if keyword.arg == 'executable' and isinstance(keyword.value, ast.Constant)]
    assert executables.count('create') == 1
    assert 'control_backend:=gazebo' in source
    assert "gz_sim.launch.py" in source
    declarations = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == 'spawners'
                            for target in node.targets)]
    assert len(declarations) == 1
    # Evaluate the real spawner declaration; another use of a controller name in
    # YAML selection must not look like a second command owner.
    spawners = eval(compile(ast.Expression(declarations[0]), str(path), 'eval'), {'Node': Node})
    context = LaunchContext()
    commands = [[perform_substitutions(context, normalize_to_list_of_substitutions(part))
                 for part in node.cmd] for node in spawners]
    expected = (
        "joint_state_broadcaster",
        "leg_position_controller",
        "arm_trajectory_controller",
        "gripper_position_controller",
    )
    assert len(commands) == len(expected)
    for controller in expected:
        assert sum(command.count(controller) for command in commands) == 1
    assert all('--controller-manager' in command and '/controller_manager' in command
               for command in commands)
    assert "TimerAction" in source
    assert "materialize_controller_config" in source
    assert "tempfile.gettempdir" in source


def test_verifier_checks_state_command_and_controller_ownership():
    source = (ROOT / "scripts/verify_gazebo_13_2.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert {
        "collect_joint_state",
        "list_controllers",
        "send_arm_goal",
        "validate_gazebo_pose",
        "write_result",
    } <= names
    assert "arm_joint_2" in source
    assert "20" in source
    assert 'choices=("gazebo", "mujoco")' in source
    assert "STATUS_SUCCEEDED" in source
    assert "SUCCESSFUL" in source

