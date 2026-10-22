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

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_gui = LaunchConfiguration('use_gui')
    xacro_file = PathJoinSubstitution(
        [FindPackageShare('integrated_robot_description'), 'urdf', 'robot_system.urdf.xacro']
    )
    description = {
        'robot_description': Command(
            [FindExecutable(name='xacro'), ' ', xacro_file, ' control_backend:=mock']
        )
    }
    return LaunchDescription(
        [
            DeclareLaunchArgument('use_gui', default_value='true'),
            Node(
                package='robot_state_publisher',
                executable='robot_state_publisher',
                parameters=[description],
            ),
            Node(
                package='joint_state_publisher_gui',
                executable='joint_state_publisher_gui',
                condition=IfCondition(use_gui),
            ),
            Node(
                package='rviz2',
                executable='rviz2',
                arguments=[
                    '-d',
                    PathJoinSubstitution(
                        [
                            FindPackageShare('integrated_robot_description'),
                            'rviz',
                            'robot_system.rviz',
                        ]
                    ),
                ],
                parameters=[{'use_sim_time': False}],
            ),
        ]
    )
