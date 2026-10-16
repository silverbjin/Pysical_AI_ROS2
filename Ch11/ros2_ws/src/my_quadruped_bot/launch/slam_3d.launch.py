"""11.6.8: level ground frame -> height-sliced PointCloud2 -> 2D SLAM."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('my_quadruped_bot')
    sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('min_height', default_value='0.3'),
        DeclareLaunchArgument('max_height', default_value='1.5'),
        DeclareLaunchArgument('cloud_topic', default_value='/lidar/points'),
        DeclareLaunchArgument('ground_height', default_value='0.0',
                              description='Known horizontal ground z in odom; not terrain estimation.'),
        DeclareLaunchArgument('start_rviz', default_value='true'),
        Node(package='my_quadruped_bot', executable='projection_frame', output='screen',
             parameters=[{'use_sim_time': sim_time, 'ground_height': ParameterValue(
                 LaunchConfiguration('ground_height'), value_type=float)}]),
        Node(package='pointcloud_to_laserscan', executable='pointcloud_to_laserscan_node',
             name='pointcloud_projection', output='screen',
             parameters=[os.path.join(share, 'config', 'pointcloud_projection.yaml'),
                         {'use_sim_time': sim_time,
                          'min_height': ParameterValue(LaunchConfiguration('min_height'), value_type=float),
                          'max_height': ParameterValue(LaunchConfiguration('max_height'), value_type=float)}],
             remappings=[('cloud_in', LaunchConfiguration('cloud_topic')), ('scan', '/scan/projected')]),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'slam.launch.py')),
            launch_arguments={
                'slam_params_file': os.path.join(share, 'config', 'mapper_params_projection.yaml'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'start_scan_filter': 'false', 'start_rviz': LaunchConfiguration('start_rviz'),
                'rviz_config': os.path.join(share, 'rviz', 'slam_3d.rviz'),
            }.items()),
    ])
