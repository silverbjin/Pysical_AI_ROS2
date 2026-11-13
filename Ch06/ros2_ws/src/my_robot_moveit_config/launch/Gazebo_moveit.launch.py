"""Ch06 §6.6: MoveIt + Gazebo Harmonic; bounded CI headless option.

Default retains the original GUI demonstration. For CI, pass
headless:=true start_rviz:=false. Controller spawners are launched after
ros_gz_sim/create has exited and run in sequence, not concurrently before
the robot's Gazebo plugin has exposed /controller_manager.
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    sim_arg = DeclareLaunchArgument("use_sim_time", default_value="true")
    headless_arg = DeclareLaunchArgument(
        "headless", default_value="false",
        description="Gazebo server only; no client rendering")
    rviz_arg = DeclareLaunchArgument(
        "start_rviz", default_value="true",
        description="Disable RViz for public headless CI")

    use_sim_time = LaunchConfiguration("use_sim_time")
    model = os.path.join(
        FindPackageShare("my_robot_description").find("my_robot_description"),
        "urdf", "my_robot.ros2_control_gazebo.urdf.xacro",
    )
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path=model)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group", executable="move_group", output="screen",
        parameters=[moveit_config.to_dict(), {"use_sim_time": use_sim_time}],
    )
    robot_state_publisher = Node(
        package="robot_state_publisher", executable="robot_state_publisher",
        output="screen", parameters=[
            moveit_config.robot_description, {"use_sim_time": use_sim_time}],
    )
    rviz_config = os.path.join(
        FindPackageShare("my_robot_moveit_config").find("my_robot_moveit_config"),
        "config", "moveit.rviz",
    )
    rviz = Node(
        package="rviz2", executable="rviz2", name="rviz2", output="screen",
        condition=IfCondition(LaunchConfiguration("start_rviz")),
        arguments=["-d", rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": use_sim_time},
        ],
    )

    gz_launch_file = os.path.join(
        FindPackageShare("ros_gz_sim").find("ros_gz_sim"),
        "launch", "gz_sim.launch.py",
    )
    # Retain existing GUI default; the same Gazebo world/model/physics are
    # launched server-only when headless=true. This does not fake sensors.
    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch_file),
        launch_arguments={"gz_args": "-r empty.sdf"}.items(),
        condition=UnlessCondition(LaunchConfiguration("headless")),
    )
    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch_file),
        launch_arguments={"gz_args": "-s -r empty.sdf"}.items(),
        condition=IfCondition(LaunchConfiguration("headless")),
    )
    spawn_entity = Node(
        package="ros_gz_sim", executable="create",
        arguments=["-topic", "robot_description", "-name", "my_robot"],
        output="screen",
    )

    spawner_options = ["--controller-manager", "/controller_manager",
                       "--controller-manager-timeout", "60"]
    broadcaster = Node(
        package="controller_manager", executable="spawner",
        arguments=["joint_state_broadcaster"] + spawner_options,
        parameters=[{"use_sim_time": use_sim_time}], output="screen",
    )
    arm = Node(
        package="controller_manager", executable="spawner",
        arguments=["arm_group_controller"] + spawner_options,
        parameters=[{"use_sim_time": use_sim_time}], output="screen",
    )

    # Sequential readiness order. If create/spawn fails, CI must still
    # classify that failure from actual launch log; action presence is
    # necessary but never sufficient for a physics acceptance verdict.
    start_broadcaster = RegisterEventHandler(
        OnProcessExit(target_action=spawn_entity, on_exit=[broadcaster])
    )
    start_arm = RegisterEventHandler(
        OnProcessExit(target_action=broadcaster, on_exit=[arm])
    )
    clock_bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    return LaunchDescription([
        sim_arg, headless_arg, rviz_arg,
        robot_state_publisher, move_group, rviz,
        gazebo_gui, gazebo_headless,
        start_broadcaster, start_arm, spawn_entity, clock_bridge,
    ])
