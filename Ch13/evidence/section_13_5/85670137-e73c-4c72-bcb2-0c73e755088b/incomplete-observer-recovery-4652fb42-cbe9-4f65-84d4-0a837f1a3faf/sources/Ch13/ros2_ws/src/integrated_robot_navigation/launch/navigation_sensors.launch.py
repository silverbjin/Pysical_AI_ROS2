"""Exactly one bound native engine; legacy launches keep their original defaults."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from integrated_robot_navigation.scene import load_scene


def select_engine(context):
    engine = LaunchConfiguration('engine').perform(context)
    directory = LaunchConfiguration('navigation_scene').perform(context)
    load_scene(engine, directory)
    share = Path(get_package_share_directory('integrated_robot_navigation'))
    description = Path(get_package_share_directory('integrated_robot_description'))
    arguments = dict(navigation_enabled='true', navigation_scene=directory, vision_enabled='true')
    if engine == 'mujoco':
        arguments.update(vision_camera_backend='snapshot', mujoco_headless='true',
                         navigation_plugins=str(share/'config/mujoco_navigation_plugins.yaml'))
    else:
        arguments['navigation_bridge'] = str(share/'config/navigation_bridge.yaml')
    actions = [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(description/'launch'/(engine+'.launch.py'))),
        launch_arguments=arguments.items())]
    if engine == 'gazebo':
        actions.append(Node(package='integrated_robot_navigation', executable='gazebo_contact_adapter',
            parameters=[{'use_sim_time': True, 'scene_dir': str(Path(directory).resolve())}]))
    return actions


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('engine', default_value='mujoco'),
        DeclareLaunchArgument('navigation_scene'), OpaqueFunction(function=select_engine)])
