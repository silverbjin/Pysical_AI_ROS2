"""Start the Ch05 Gazebo arm and controllers with checked sequencing."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import EmitEvent, IncludeLaunchDescription, LogError, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import xacro


def _after_exit(event, next_action, step_name):
    """Proceed only if the completed Gazebo/spawner process exited successfully."""
    if event.returncode == 0:
        return [next_action]
    reason = f'{step_name} failed (returncode={event.returncode}); stopping launch'
    return [LogError(msg=reason), EmitEvent(event=Shutdown(reason=reason))]


def generate_launch_description():
    pkg = get_package_share_directory('manipulation_basics')
    pkg_gazebo = get_package_share_directory('ros_gz_sim')
    robot_urdf = xacro.process_file(os.path.join(pkg, 'urdf', 'robot.urdf.xacro')).toxml()

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_gazebo, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_urdf, 'use_sim_time': True}],
    )
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'physical_ai_robot', '-z', '0.05'],
        output='screen',
    )
    common = ['--controller-manager', '/controller_manager',
              '--controller-manager-timeout', '30', '--switch-timeout', '30']
    jsb = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', *common],
        output='screen',
    )
    arm = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', *common],
        output='screen',
    )
    # OnProcessExit fires on success AND failure: never continue after a failure.
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn,
                      on_exit=lambda event, context: _after_exit(event, jsb, 'Gazebo create')),
    )
    # A completed spawner with exit code zero is a stronger readiness gate than
    # sleeping 2 seconds after the spawner process starts.
    after_jsb = RegisterEventHandler(
        OnProcessExit(target_action=jsb,
                      on_exit=lambda event, context: _after_exit(event, arm, 'JSB spawner')),
    )
    rviz_file = PathJoinSubstitution(
        [FindPackageShare('manipulation_basics'), 'rviz', 'manipulation.rviz'],
    )
    rviz = Node(package='rviz2', executable='rviz2', name='rviz2',
                arguments=['-d', rviz_file], parameters=[{'use_sim_time': True}],
                output='screen')
    return LaunchDescription([
        gazebo, robot_state_publisher, clock_bridge, after_spawn, after_jsb,
        spawn, rviz,
    ])
