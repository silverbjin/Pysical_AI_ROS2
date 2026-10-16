import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # 1. 런치 인자 정의 (가제보 환경이므로 기본값을 true로 강제하거나 명시적 선언)
    sim_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="true", description="Use simulation clock if true"
    )
    use_sim_time = LaunchConfiguration("use_sim_time")
    
    # 2. MoveItConfigsBuilder를 통한 설정 일괄 로드
    # (통합 래퍼 파일인 my_robot.ros2_control_gazebo.urdf.xacro를 명시적으로 타겟팅합니다)
    robot_description_path = os.path.join(
        FindPackageShare("my_robot_description").find("my_robot_description"),
        "urdf",
        "my_robot.ros2_control_gazebo.urdf.xacro",
    )
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        # .robot_description(file_path="urdf/my_robot_control.urdf.xacro")
        .robot_description(file_path=robot_description_path)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    # 3. move_group 노드 설정 (데모 파일의 무결성 구조 유지)
    run_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": use_sim_time}
        ],
    )

    # 4. Robot State Publisher 노드
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            {"use_sim_time": use_sim_time}
        ],
    )

    # 5. RViz2 시각화 노드 설정
    rviz_config_path = os.path.join(
        FindPackageShare("my_robot_moveit_config").find("my_robot_moveit_config"),
        "config",
        "moveit.rviz",
    )
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": use_sim_time}
        ],
    )

    # ================= 가제보 시뮬레이션 환경 전용 추가 항목 =================

    # 6. 모던 가제보 (gz_sim) 실행
    gz_sim_pkg = FindPackageShare('ros_gz_sim').find('ros_gz_sim')
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gz_sim_pkg, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()  # -r로 시작 시 일시정지 해제
    )

    # 7. 가제보 내부에 로봇 엔티티 소환 (ros_gz_sim 규격 사용)
    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-topic", "robot_description",
            "-name", "my_robot"
        ],
        output="screen",
    )

    # 8. 컨트롤러 Spawner 등록 
    # (★ 중요: 가제보 내장 플러그인이 매니저 역할을 하므로 ros2_control_node는 띄우지 않습니다)
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "controller_manager"],
        parameters=[{"use_sim_time": use_sim_time}]
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        # 기존 데모의 'arm_group_controller' 이름을 유지하되 실제 설정을 따릅니다.
        arguments=["arm_group_controller", "--controller-manager", "controller_manager"],
        parameters=[{"use_sim_time": use_sim_time}]
    )
 
    # degug: 'No clock received, using time argument instead!' 문제 해결을 위한 브리지 노드 추가
    clock_bridge = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
    output='screen'
)

    return LaunchDescription(
        [
            sim_arg,
            robot_state_publisher_node,
            run_move_group_node,
            rviz_node,
            
            # 가제보 및 월드 소환 관련
            gazebo_launch,
            spawn_entity,
            
            # 컨트롤러 가동 관련
            joint_state_broadcaster_spawner,
            arm_controller_spawner,
            
            clock_bridge
        ]
    )