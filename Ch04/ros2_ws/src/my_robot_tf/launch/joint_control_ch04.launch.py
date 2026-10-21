"""4.7절: Ch03 모델의 joint1 Gazebo 위치 명령 브리지와 ROS 제어 노드."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=[
                "/model/my_robot/joint1/cmd_pos"
                "@std_msgs/msg/Float64]gz.msgs.Double",
            ],
            remappings=[
                ("/model/my_robot/joint1/cmd_pos", "/joint1/cmd_pos"),
            ],
            output="screen",
        ),
        Node(
            package="my_robot_tf",
            executable="joint_position_cli",
            parameters=[{"joint_name": "joint1", "amplitude": 0.785}],
            output="screen",
        ),
    ])
