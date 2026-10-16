from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    """
    런치 파일의 진입점 함수.
    반드시 'LaunchDescription' 객체를 반환해야 한다.
    """
    
    # 1. Turtlesim 노드 정의
    # 패키지: turtlesim
    # 실행파일: turtlesim_node
    # 노드이름: sim (기본 이름을 덮어씀)
    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        name='sim',
        output='screen' # 로그를 터미널에 출력
    )

    # 2. 나의 커스텀 퍼블리셔 노드 정의
    # 패키지: my_robot_system
    # 실행파일: turtle_cmd_pub (setup.py의 console_scripts 이름)
    my_pub_node = Node(
        package='my_robot_system',
        executable='turtle_cmd_pub',
        name='my_publisher',
        output='screen'
    )

    # 3. 나의 커스텀 서브스크라이버 노드 정의
    my_sub_node = Node(
        package='my_robot_system',
        executable='turtle_pose_sub',
        name='my_subscriber',
        output='screen'
    )

    # 정의된 노드들을 리스트에 담아 반환
    return LaunchDescription([
        turtlesim_node,
        my_pub_node,
        my_sub_node
    ])
