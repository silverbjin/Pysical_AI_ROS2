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
import os
from pathlib import Path
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.actions import IncludeLaunchDescription
from launch.actions import RegisterEventHandler
from launch.actions import TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def materialize_controller_config(source):
    """Copy YAML to a short native path for gz_ros2_control Jazzy issue #512."""
    data = Path(source).read_bytes()
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = Path(tempfile.gettempdir()) / f'ch13_2_controllers_{digest}.yaml'
    if not target.exists() or target.read_bytes() != data:
        temporary = target.with_suffix('.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
    return str(target)


def launch_nodes(context):
    package_share = get_package_share_directory('integrated_robot_description')
    vision = LaunchConfiguration('vision_enabled').perform(context).lower() == 'true'
    world = LaunchConfiguration('world').perform(context) or os.path.join(
        package_share, 'worlds', 'vision_fixture.sdf' if vision else 'empty.sdf')
    xacro_path = os.path.join(package_share, 'urdf', 'robot_system.urdf.xacro')
    controllers = materialize_controller_config(
        os.path.join(package_share, 'config', 'controllers.yaml')
    )
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
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': ['-r -s ', '--headless-rendering ' if vision else '', world]}.items(),
    )
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
        arguments=['-topic', 'robot_description', '-name', 'integrated_robot', '-z', '0.52'],
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
                 parameters=[{'config_file': os.path.join(package_share, 'config', 'vision_bridge.yaml')}]),
            Node(package='integrated_robot_vision', executable='native_pose_adapter',
                 parameters=[{'engine': 'gazebo', 'use_sim_time': True}]),
        ])
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('vision_enabled', default_value='false'),
        DeclareLaunchArgument('world', default_value=''),
        OpaqueFunction(function=launch_nodes),
    ])
