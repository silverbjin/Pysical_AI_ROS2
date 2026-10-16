"""11.2.4 processor only; start one Gazebo simulation in another terminal."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('alpha', default_value='0.98'),
        DeclareLaunchArgument('max_dt', default_value='0.2'),
        DeclareLaunchArgument('input_topic', default_value='/imu/data_raw'),
        DeclareLaunchArgument('output_topic', default_value='/imu/rpy_filtered'),
        Node(package='my_quadruped_bot', executable='imu_processor',
             name='imu_processor', output='screen',
             parameters=[{
                 'use_sim_time': ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool),
                 'alpha': ParameterValue(LaunchConfiguration('alpha'), value_type=float),
                 'max_dt': ParameterValue(LaunchConfiguration('max_dt'), value_type=float),
             }],
             remappings=[('/imu/data_raw', LaunchConfiguration('input_topic')),
                         ('/imu/rpy_filtered', LaunchConfiguration('output_topic'))]),
    ])
