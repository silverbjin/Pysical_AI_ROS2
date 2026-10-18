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
from launch.actions import DeclareLaunchArgument
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


def generate_launch_description():
    package_share = get_package_share_directory('integrated_robot_description')
    world = LaunchConfiguration('world')
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
        launch_arguments={'gz_args': ['-r -s ', world]}.items(),
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
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'world', default_value=os.path.join(package_share, 'worlds', 'empty.sdf')
            ),
            gazebo,
            state_publisher,
            clock_bridge,
            spawn_robot,
            start_controllers,
        ]
    )
