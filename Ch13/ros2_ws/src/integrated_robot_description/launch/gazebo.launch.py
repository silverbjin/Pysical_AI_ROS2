# Copyright 2026 Jinho
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, ExecuteProcess, Shutdown
from launch.actions import IncludeLaunchDescription
from launch.actions import RegisterEventHandler
from launch.actions import TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import yaml


def materialize_controller_config(source, *, vision=False):
    """Copy YAML to a short native path for gz_ros2_control Jazzy issue #512."""
    data = Path(source).read_bytes()
    if vision:
        config = yaml.safe_load(data)
        config['controller_manager']['ros__parameters']['arm_trajectory_controller']['type'] = (
            'integrated_robot_controller/JointTrajectoryController')
        data = yaml.safe_dump(config, sort_keys=False).encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = Path(tempfile.gettempdir()) / f'ch13_2_controllers_{digest}.yaml'
    if not target.exists() or target.read_bytes() != data:
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
    return str(target)


def navigation_gazebo_action(world, vision):
    """Direct Ruby/native server PID; preserve upstream resource/plugin paths.

    Only the opt-in navigation scene uses this. Legacy 13.4 still includes the
    upstream launch unchanged. Import its installed path helper, never copy or
    patch the external launcher merely to remove its shell=True wrapper.
    """
    launcher = Path(get_package_share_directory('ros_gz_sim'))/'launch/gz_sim.launch.py'
    spec = importlib.util.spec_from_file_location('_ch13_gazebo_paths', launcher)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    model_paths, plugin_paths = upstream.GazeboRosPaths.get_paths()
    environment = {
        'GZ_SIM_SYSTEM_PLUGIN_PATH': os.pathsep.join([
            os.environ.get('GZ_SIM_SYSTEM_PLUGIN_PATH', ''),
            os.environ.get('LD_LIBRARY_PATH', ''), plugin_paths]),
        'GZ_SIM_RESOURCE_PATH': os.pathsep.join([
            os.environ.get('GZ_SIM_RESOURCE_PATH', ''), model_paths]),
    }
    command = [upstream.get_executable_path('ruby'), upstream.get_executable_path('gz'),
               'sim', '-r', '-s']
    if vision:
        command.append('--headless-rendering')
    command.extend([str(world), '--force-version', '8'])
    # Match the upstream on_exit_shutdown lifecycle: let ProcessExited finish
    # the launch service rather than racing its async cleanup with parent SIGINT.
    return ExecuteProcess(cmd=command, name='gazebo', shell=False,
                          additional_env=environment, output='screen',
                          on_exit=Shutdown(reason='owned navigation Gazebo process exited'))


def launch_nodes(context):
    package_share = get_package_share_directory('integrated_robot_description')
    vision = LaunchConfiguration('vision_enabled').perform(context).lower() == 'true'
    navigation = LaunchConfiguration('navigation_enabled', default='false').perform(context).lower() == 'true'
    scene = None
    if navigation:
        from integrated_robot_navigation.scene import load_scene
        scene = load_scene('gazebo', LaunchConfiguration('navigation_scene').perform(context))
        if not vision:
            raise ValueError('navigation scene requires vision_enabled')
    world = LaunchConfiguration('world').perform(context) or os.path.join(
        package_share, 'worlds', 'vision_fixture.sdf' if vision else 'empty.sdf')
    if scene:
        requested = LaunchConfiguration('world').perform(context)
        if requested and Path(requested).resolve() != Path(scene['world']['path']).resolve():
            raise ValueError('navigation world must match bound scene')
        world = scene['world']['path']
    xacro_path = os.path.join(package_share, 'urdf', 'robot_system.urdf.xacro')
    controllers = materialize_controller_config(
        os.path.join(package_share, 'config', 'controllers.yaml'), vision=vision
    )
    if scene:
        controllers = scene['native_controllers']['path']
    description = ParameterValue(
        Command(
            [
                'xacro ',
                xacro_path,
                ' control_backend:=gazebo controllers_file:=',
                controllers,
                ' vision_enabled:=', str(vision).lower(),
            ]
        ),
        value_type=str,
    )
    if scene:
        description = ParameterValue(Path(scene['robot']['path']).read_text(), value_type=str)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': ['-r -s ', '--headless-rendering ' if vision else '', world]}.items(),
    )
    if scene:
        gazebo = navigation_gazebo_action(world, vision)
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': description, 'use_sim_time': True}],
        output='screen',
    )
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=([ '-file', scene['robot_sdf']['path']] if scene else
                   ['-topic', 'robot_description']) + ['-name', 'integrated_robot', '-z', '0.52'],
        output='screen',
    )
    spawners = [
        Node(
            package='controller_manager',
            executable='spawner',
            arguments=[
                name,
                '--controller-manager',
                '/controller_manager',
                '--controller-manager-timeout',
                '30',
            ],
            output='screen',
        )
        for name in (
            'joint_state_broadcaster',
            'leg_position_controller',
            'arm_trajectory_controller',
            'gripper_position_controller',
        )
    ]
    start_controllers = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_robot,
            on_exit=[TimerAction(period=2.0, actions=spawners)],
        )
    )
    nodes = [
            gazebo,
            state_publisher,
            clock_bridge,
            spawn_robot,
            start_controllers,
        ]
    if vision:
        nodes.extend([
            Node(package='ros_gz_bridge', executable='parameter_bridge',
                 parameters=[{'config_file': os.path.join(
                     package_share, 'config', 'vision_bridge.yaml') if not navigation else
                     LaunchConfiguration('navigation_bridge').perform(context)}]),
            Node(package='integrated_robot_vision', executable='native_pose_adapter',
                 parameters=[{'engine': 'gazebo', 'use_sim_time': True}]),
        ])
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('vision_enabled', default_value='false'),
        DeclareLaunchArgument('world', default_value=''),
        DeclareLaunchArgument('navigation_enabled', default_value='false'),
        DeclareLaunchArgument('navigation_scene', default_value=''),
        DeclareLaunchArgument('navigation_bridge', default_value=''),
        OpaqueFunction(function=launch_nodes),
    ])
