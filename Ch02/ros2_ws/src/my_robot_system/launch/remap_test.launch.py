from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    # 1. Turtlesim을 실행하되, 배경을 빨간색으로 변경 (Parameter)
    # Turtlesim은 background_r, g, b 파라미터를 지원한다.
    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='sim',
        # (수정 예시) Turtlesim 노드 설정에 추가
        # remappings=[
        #     ('/turtle1/cmd_vel', '/cmd_vel_custom')
        # ], 
        parameters=[
            {'background_r': 200},
            {'background_g': 0},
            {'background_b': 0}
        ]
    )

    # 2. 퍼블리셔 실행하되, 토픽 이름을 변경 (Remapping)
    # 기존: /turtle1/cmd_vel -> 변경: /cmd_vel_custom
    my_pub_node = Node(
        package='my_robot_system',
        executable='turtle_cmd_pub',
        name='my_publisher',
        remappings=[
            ('/turtle1/cmd_vel', '/cmd_vel_custom')
        ]
    )

    # 3. 서브스크라이버는 실행하지 않음 (비교를 위해)

    return LaunchDescription([
        turtlesim_node,
        my_pub_node
    ])
