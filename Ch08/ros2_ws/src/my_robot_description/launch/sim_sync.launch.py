import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
# [해결책] 거대 XML(URDF) 문자열 파싱 오류를 방지하기 위한 클래스 임포트
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 1. 패키지 경로 및 설정 변수
    pkg_name = 'my_robot_description'
    pkg_share = get_package_share_directory(pkg_name)   # 패키지 공유 디렉토리 경로
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # 3장에서 만든 xacro 파일
    xacro_file = os.path.join(pkg_share, 'urdf', 'two_dof_arm.urdf.xacro')
    
    # RViz 설정 파일 (미리 저장해두었다면 경로 지정)
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'display.rviz')

    # 2. Launch Argument 설정 (사용자 편의성)
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # 3. Robot State Publisher (RSP) 실행
    # Xacro를 URDF로 변환하여 robot_description 파라미터로 전달
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time, 
            # 'robot_description': Command(['xacro ', xacro_file])
            # [해결책] URDF 문자열이 너무 길어서 발생하는 파싱 오류 방지
            'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
        }]
    )
    
    # [부적절] Joint State Publisher 노드 설정 for TF broadcasting 
    # 이유는 디지털 트윈을 구축기 위해선 ROS2에서 TF broadcasting할 게 아니라, 
    # Gazebo (or Real Robot)에서 발행하는 joint_states를 RSP가 구독해서 TF를 브로드캐스팅하는 방식이 적절하다.다
    # joint_state_publisher_node = Node(
    #     package='joint_state_publisher',
    #     executable='joint_state_publisher',
    #     name='joint_state_publisher'
    # )

    # 4. Gazebo Simulator 실행
    # ros_gz_sim 패키지의 launch 파일을 포함시킨다.
    # -r 옵션: 실행 즉시 시뮬레이션 시작 (Pause 상태 아님)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # 5. 로봇 스폰 (Spawn) 노드
    # Gazebo 안에 우리 로봇 모델을 생성한다.
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description', # RSP가 발행한 토픽에서 모델 정보를 가져옴
            '-name', 'my_robot',
            '-z', '0.5' # 바닥에 묻히지 않게 약간 띄워서 생성
        ],
        output='screen'
    )

    # 6. ROS-Gazebo Bridge (핵심!)
    # topic@ros_type[gz_type 형식으로 매핑을 정의한다.
    # /clock -> ROS로 시간 동기화 (단방향)
    # /world/empty/model/my_robot/joint_state -> ROS(/joint_states)로 관절 정보 전송 (단방향)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            # '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',            
            '/world/empty/model/my_robot/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model',
            # [해설] @: "gazebo 토픽(/world/empty/model/my_robot/joint_state)은 ROS에서는 sensor_msgs/msg/JointState 타입입니다"
            # [해설] [: "Gazebo의 gz.msgs.Model 타입을 ROS의 sensor_msgs/msg/JointState 타입으로 변환"
            '/model/my_robot/joint1/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',  # joint1 ROS->Gazebo bridge
            '/model/my_robot/joint2/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double',  # 제어 명령을 ROS에서 받아서 Gazebo로 전달 (단방향)
        ],
        remappings=[
        (
            '/world/empty/model/my_robot/joint_state',  # Gazebo에서 발행하는 실제 joint_states 토픽
            '/joint_states', # ROS에서 RSP가 구독하는 토픽으로 remap (중요! RSP가 이 토픽을 구독해야 TF broadcasting이 제대로 작동)
        ),
        ('/model/my_robot/joint1/cmd_pos', '/joint1/cmd_pos'),
        ('/model/my_robot/joint2/cmd_pos', '/joint2/cmd_pos'),
    ],
        output='screen'
    )

    # 7. RViz2 실행
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}], # 중요: RViz도 use_sim_time을 써야 함
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        
        robot_state_publisher,# RSP가 'robo _description' 토픽에서 모델 정보를 발행한다. Gazebo보다 먼저 실행되어야 한다.
        gazebo,
        spawn_entity, # spawn_entity는 'robot_description' 토픽에서 모델 정보를 가져와서 Gazebo에 로봇을 생성한다. 따라서 RSP가 먼저 실행되어야 한다. (순서 중요)
        # joint_state_publisher_node, #[부적절] RSP가 Gazebo에서 발행하는 joint_states를 구독해서 TF를 브로드캐스팅하는 방식이 적절
        bridge,
        rviz
    ])

# [참고] spawn_entity의 의존관계
# robot_state_publisher
#         │
#         └── publishes /robot_description
#                      │
#                      ▼
#                 spawn_entity
#                      ▲
#                      │
#                Gazebo server running