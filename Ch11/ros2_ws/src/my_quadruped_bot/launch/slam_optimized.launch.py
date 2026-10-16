"""11.6 switchable tuning profiles and either IMU or EKF-TF scan gating."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def compose(context):
    share = get_package_share_directory('my_quadruped_bot')
    profile = LaunchConfiguration('profile').perform(context)
    mode = LaunchConfiguration('stabilizer').perform(context)
    config = os.path.join(share, 'config', f'mapper_params_{profile}.yaml')
    executable = 'scan_stabilizer' if mode == 'imu' else 'slam_scan_filter'
    params = {'use_sim_time': True, 'output_topic': '/scan_stabilized',
              'max_tilt_degrees': ParameterValue(LaunchConfiguration('max_tilt_degrees'), value_type=float),
              'min_scan_interval': ParameterValue(LaunchConfiguration('min_scan_interval'), value_type=float)}
    if mode == 'imu':
        params['max_imu_delta'] = ParameterValue(LaunchConfiguration('max_imu_delta'), value_type=float)
    return [
        Node(package='my_quadruped_bot', executable=executable, output='screen', parameters=[params]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'slam.launch.py')),
            launch_arguments={'slam_params_file': config, 'start_scan_filter': 'false',
                              'start_rviz': LaunchConfiguration('start_rviz')}.items()),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('profile', default_value='balanced', choices=['balanced', 'wide_search']),
        DeclareLaunchArgument('stabilizer', default_value='imu', choices=['imu', 'tf']),
        DeclareLaunchArgument('max_tilt_degrees', default_value='5.0'),
        DeclareLaunchArgument('max_imu_delta', default_value='0.03'),
        DeclareLaunchArgument('min_scan_interval', default_value='0.15'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        OpaqueFunction(function=compose),
    ])
