"""4.6절: Gazebo Harmonic 관절 상태 → ROS JointState → RSP → RViz.

참고: world→base_link의 *실제 자유 몸체 포즈* 동기화는 포함하지 않는다.
Ch03 my_robot_description 패키지가 설치된 overlay를 필요로 한다.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    model_share = get_package_share_directory("my_robot_description")
    model_file = os.path.join(model_share, "urdf", "two_dof_arm.urdf.xacro")
    if not os.path.isfile(model_file):
        raise FileNotFoundError(
            "Expected Ch03 model: " + model_file + "; source Ch03/ros2_ws"
        )

    rviz_file = os.path.join(
        get_package_share_directory("my_robot_tf"), "rviz", "sim_sync_ch04.rviz"
    )
    gazebo_launch = os.path.join(
        get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"
    )
    use_sim_time = LaunchConfiguration("use_sim_time")
    description = ParameterValue(Command(["xacro ", model_file]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        Node(
            package="robot_state_publisher", executable="robot_state_publisher",
            name="robot_state_publisher",
            parameters=[{"use_sim_time": use_sim_time,
                         "robot_description": description}],
            output="screen",
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(gazebo_launch),
            launch_arguments={"gz_args": "-r empty.sdf"}.items(),
        ),
        Node(
            package="ros_gz_sim", executable="create",
            arguments=["-topic", "robot_description", "-name", "my_robot",
                       "-z", "0.5"],
            output="screen",
        ),
        Node(
            package="ros_gz_bridge", executable="parameter_bridge",
            arguments=[
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                "/world/empty/model/my_robot/joint_state"
                "@sensor_msgs/msg/JointState[gz.msgs.Model",
            ],
            remappings=[
                ("/world/empty/model/my_robot/joint_state", "/joint_states"),
            ],
            output="screen",
        ),
        Node(
            package="rviz2", executable="rviz2",
            arguments=["-d", rviz_file],
            parameters=[{"use_sim_time": use_sim_time}], output="screen",
        ),
    ])
