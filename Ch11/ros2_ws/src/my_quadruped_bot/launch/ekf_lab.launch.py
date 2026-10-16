"""Isolated 11.4 demo; existing localization.launch.py remains the default."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('my_quadruped_bot')
    sim = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    acceleration = LaunchConfiguration('use_acceleration')
    configs = [('ekf_command_lab.yaml', UnlessCondition(acceleration)),
               ('ekf_command_lab_accel.yaml', IfCondition(acceleration))]
    declarations = [DeclareLaunchArgument(name, default_value=value) for name, value in (
        ('use_sim_time', 'true'), ('use_acceleration', 'false'),
        ('command_topic', '/cmd_vel'), ('scale', '0.9'),
        ('noise_stddev', '0.01'), ('angular_noise_stddev', '0.005'),
    )]
    source = Node(
        package='my_quadruped_bot', executable='leg_odometry', output='screen',
        parameters=[{'use_sim_time': sim, **{
            name: ParameterValue(LaunchConfiguration(name), value_type=float)
            for name in ('scale', 'noise_stddev', 'angular_noise_stddev')}}],
        remappings=[('/cmd_vel', LaunchConfiguration('command_topic'))])
    imu = Node(package='my_quadruped_bot', executable='ekf_lab_imu', output='screen',
               parameters=[{'use_sim_time': sim, 'require_orientation':
                            ParameterValue(acceleration, value_type=bool)}])
    filters = [Node(package='robot_localization', executable='ekf_node',
                    name='ekf_lab_filter', output='screen', condition=condition,
                    parameters=[os.path.join(share, 'config', config), {'use_sim_time': sim}],
                    remappings=[('/odometry/filtered', '/ekf_lab/filtered')])
               for config, condition in configs]
    return LaunchDescription(declarations + [source, imu] + filters)
