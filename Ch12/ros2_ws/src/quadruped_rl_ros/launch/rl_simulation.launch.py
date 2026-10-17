"""One controller, one simulator. Safe default: policy monitor only."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction,IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from quadruped_rl_ros.gazebo_description import prepare_description


def setup(context):
    backend=LaunchConfiguration('backend').perform(context)
    enabled=LaunchConfiguration('enabled').perform(context).lower()=='true'
    bundle=LaunchConfiguration('bundle_path').perform(context)
    nodes=[Node(package='quadruped_rl_ros',executable='rl_controller',output='screen',
        parameters=[dict(use_sim_time=True,backend=backend,enabled=enabled,bundle_path=bundle)])]
    if backend=='mujoco':
        nodes.insert(0,Node(package='quadruped_rl_ros',executable='mujoco_bridge',output='screen'))
    elif backend=='gazebo':
        share=get_package_share_directory('my_quadruped_bot')
        description=prepare_description(os.path.join(share,'urdf','robot.urdf.xacro'))
        gz_share=get_package_share_directory('ros_gz_sim')
        nodes[:0]=[
            IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(gz_share,'launch','gz_sim.launch.py')),
                launch_arguments={'gz_args':'-r -s '+os.path.join(share,'worlds','empty_world.sdf')}.items()),
            Node(package='robot_state_publisher',executable='robot_state_publisher',
                 parameters=[{'robot_description':description,'use_sim_time':True}]),
            Node(package='ros_gz_sim',executable='create',arguments=['-topic','robot_description',
                 '-name','my_quadruped','-z','.5'],output='screen'),
            Node(package='ros_gz_bridge',executable='parameter_bridge',output='screen',
                 parameters=[{'config_file':os.path.join(share,'config','ros_gz_bridge.yaml')}])]
    else:raise ValueError('backend must be mujoco or gazebo')
    return nodes


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('backend',default_value='mujoco'),
        DeclareLaunchArgument('enabled',default_value='false'),
        DeclareLaunchArgument('bundle_path'),OpaqueFunction(function=setup)])
