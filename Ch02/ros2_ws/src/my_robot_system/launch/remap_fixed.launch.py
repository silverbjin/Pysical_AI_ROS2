"""양쪽 끝점을 함께 리매핑하여 거북이를 실제로 움직이는 예제."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='turtlesim', executable='turtlesim_node', name='sim',
            output='screen',
            parameters=[
                {'background_r': 200},
                {'background_g': 0},
                {'background_b': 0},
            ],
            remappings=[('/turtle1/cmd_vel', '/cmd_vel_custom')],
        ),
        Node(
            package='my_robot_system', executable='turtle_cmd_pub',
            name='my_publisher', output='screen',
            remappings=[('/turtle1/cmd_vel', '/cmd_vel_custom')],
        ),
        Node(
            package='my_robot_system', executable='turtle_pose_sub',
            name='my_subscriber', output='screen',
        ),
    ])
