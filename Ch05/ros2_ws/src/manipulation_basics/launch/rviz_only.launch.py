"""Run just RViz for an existing Ch05 /robot_description + /joint_states graph."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    configuration = PathJoinSubstitution(
        [FindPackageShare('manipulation_basics'), 'rviz', 'manipulation.rviz'])
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', configuration],
             parameters=[{'use_sim_time': ParameterValue(
                 LaunchConfiguration('use_sim_time'), value_type=bool)}],
             output='screen'),
    ])
