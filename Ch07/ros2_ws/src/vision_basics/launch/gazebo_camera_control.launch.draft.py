import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # 1. 패키지 경로 및 설정 변수
    pkg_name = 'vision_basics'  # 독자의 실습 환경에 따라 패키지명이 다를 수 있음을 본문에 명시해야 합니다.
    pkg_share = get_package_share_directory(pkg_name)   
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    
    # 앞서 생성한 비전 통합 Xacro 파일 경로
    xacro_file = os.path.join(pkg_share, 'urdf', 'my_robot.ros2_camera_control_gazebo.urdf.xacro')
    
    # RViz 설정 파일 경로
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'display.rviz')

    # 2. Launch Argument 설정
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    # 3. Robot State Publisher (RSP) 실행
    # Xacro 파싱 오류를 방지하기 위해 ParameterValue 사용
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time, 
            'robot_description': ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
        }]
    )
    
    # 4. Gazebo Simulator 실행
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items(),
    )

    # 5. 로봇 스폰 (Spawn) 노드
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description', 
            '-name', 'my_robot',
            '-z', '0.5' 
        ],
        output='screen'
    )

    # 6. ROS-Gazebo 파라미터 브리지
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/world/empty/model/my_robot/joint_state@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/model/my_robot/joint2/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double', 
            # 카메라 정보 (Intrinsic) 브리지 - 양방향(@) 통신 허용
            '/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo'
        ],
        remappings=[
            ('/world/empty/model/my_robot/joint_state', '/joint_states'),
            ('/model/my_robot/joint2/cmd_pos', '/joint2/cmd_pos'),
        ],
        output='screen'
    )

    # 7. ROS-Gazebo 이미지 전용 브리지 (권장 사항)
    # 이미지 데이터는 parameter_bridge 대신 image_bridge를 사용하는 것이 성능상 안전함
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    # 8. RViz2 실행
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}], 
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),
        
        robot_state_publisher,
        gazebo,
        spawn_entity, 
        bridge,
        image_bridge,  # 추가된 이미지 브리지
        rviz
    ])