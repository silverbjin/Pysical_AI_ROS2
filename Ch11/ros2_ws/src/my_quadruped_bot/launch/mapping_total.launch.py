"""11.7 integrated maze mapping; motion begins only after readiness gates."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share=get_package_share_directory('my_quadruped_bot')
    def include(name,args):
        return GroupAction([IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(share,'launch',name)),launch_arguments=args.items())])
    return LaunchDescription([
        DeclareLaunchArgument('start_explorer',default_value='false',
                              description='Explicitly enable autonomous motion after sensor/TF/map readiness.'),
        DeclareLaunchArgument('rviz',default_value='true'),
        DeclareLaunchArgument('profile',default_value='balanced',choices=['balanced','wide_search']),
        DeclareLaunchArgument('duration',default_value='300.0'),
        DeclareLaunchArgument('output_dir',default_value=os.path.expanduser('~/Pysical_AI_maps')),
        include('SLAM_simulation.launch.py',{'start_rviz':'false','lidar_3d':'false',
            'world':os.path.join(share,'worlds','maze_room.sdf')}),
        include('slam_optimized.launch.py',{'start_rviz':LaunchConfiguration('rviz'),
            'profile':LaunchConfiguration('profile'),'stabilizer':'imu'}),
        Node(package='my_quadruped_bot',executable='imu_processor',output='screen',
             parameters=[{'use_sim_time':True}]),
        Node(package='my_quadruped_bot',executable='autonomous_explorer',output='screen',
             condition=IfCondition(LaunchConfiguration('start_explorer')),
             parameters=[os.path.join(share,'config','exploration.yaml'),
                         {'output_dir':LaunchConfiguration('output_dir'),
                          'duration':ParameterValue(LaunchConfiguration('duration'),value_type=float)}]),
    ])
