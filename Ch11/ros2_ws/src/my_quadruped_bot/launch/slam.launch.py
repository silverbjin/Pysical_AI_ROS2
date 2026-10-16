"""Online mapping only: existing simulation/localization must already be running."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('my_quadruped_bot')
    sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        DeclareLaunchArgument('slam_params_file', default_value=os.path.join(
            share, 'config', 'mapper_params_online_async.yaml')),
        DeclareLaunchArgument('max_tilt_degrees', default_value='5.0'),
        DeclareLaunchArgument('min_scan_interval', default_value='0.15'),
        Node(package='my_quadruped_bot', executable='slam_scan_filter',
             output='screen', parameters=[{
                 'use_sim_time': sim_time,
                 'max_tilt_degrees': ParameterValue(
                     LaunchConfiguration('max_tilt_degrees'), value_type=float),
                 'min_scan_interval': ParameterValue(
                     LaunchConfiguration('min_scan_interval'), value_type=float),
             }]),
        # Jazzy uses a lifecycle node. The upstream launch configures and activates it.
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')),
            launch_arguments={
                'slam_params_file': LaunchConfiguration('slam_params_file'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'autostart': 'true',
                'use_lifecycle_manager': 'false',
            }.items()),
        Node(package='rviz2', executable='rviz2', name='slam_rviz',
             arguments=['-d', os.path.join(share, 'rviz', 'slam.rviz')],
             parameters=[{'use_sim_time': sim_time}],
             condition=IfCondition(LaunchConfiguration('start_rviz'))),
    ])
