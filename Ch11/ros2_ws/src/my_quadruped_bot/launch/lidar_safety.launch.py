"""11.3.4 scan monitor only. Run one simulation separately."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('safe_distance', default_value='0.5'),
        DeclareLaunchArgument('scope_deg', default_value='30.0'),
        DeclareLaunchArgument('scan_timeout', default_value='0.5'),
        DeclareLaunchArgument('input_topic', default_value='/scan'),
        DeclareLaunchArgument('output_topic', default_value='/lidar_safety/status'),
        DeclareLaunchArgument('expected_frame', default_value='lidar_link'),
        Node(package='my_quadruped_bot', executable='lidar_safety',
             name='lidar_safety', output='screen', parameters=[{
                 'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
                 'safe_distance': ParameterValue(LaunchConfiguration('safe_distance'), value_type=float),
                 'scope_deg': ParameterValue(LaunchConfiguration('scope_deg'), value_type=float),
                 'scan_timeout': ParameterValue(LaunchConfiguration('scan_timeout'), value_type=float),
                 'expected_frame': ParameterValue(LaunchConfiguration('expected_frame'), value_type=str),
             }], remappings=[
                 ('/scan', LaunchConfiguration('input_topic')),
                 ('/lidar_safety/status', LaunchConfiguration('output_topic'))]),
    ])
