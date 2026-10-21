"""4.2절: Jazzy용 명명 인수로 다중 정적 TF를 게시한다."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    rviz_config = os.path.join(
        get_package_share_directory("my_robot_tf"), "rviz", "multi_static_tf.rviz"
    )
    return LaunchDescription([
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            arguments=[
                "--x", "0", "--y", "0", "--z", "1",
                "--roll", "0", "--pitch", "0", "--yaw", "0",
                "--frame-id", "world", "--child-frame-id", "base_link",
            ],
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            arguments=[
                "--x", "0.1", "--y", "0", "--z", "0.2",
                "--roll", "0", "--pitch", "0", "--yaw", "0",
                "--frame-id", "base_link", "--child-frame-id", "lidar_sensor_link",
            ],
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz2",
            arguments=["-d", rviz_config], output="screen",
        ),
    ])
