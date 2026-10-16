import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # 1. 런치 인자 정의 (가상 하드웨어 사용 여부 등)
    sim_arg = DeclareLaunchArgument(
        "use_sim_time", default_value="false", description="Use simulation clock if true"
    )

    # 2. MoveItConfigsBuilder를 통한 설정 일괄 로드
    # 지정한 패키지의 config/ 폴더 내 전형적인 파일명(ompl_planning.yaml, kinematics.yaml 등)을 자동 인지합니다.
    robot_description_path = os.path.join(
        FindPackageShare("my_robot_description").find("my_robot_description"),
        "urdf",
        "my_robot.ros2_control_rviz.urdf.xacro",     
    )
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        # .robot_description(file_path="config/my_robot.urdf.xacro")
        .robot_description(file_path=robot_description_path)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    # 3. move_group 노드 설정
    run_move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        # 파라미터 딕셔너리를 일괄 주입하여 네임스페이스 누수를 차단합니다.
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": LaunchConfiguration("use_sim_time")}
        ],
    )

    # 4. Robot State Publisher 노드
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            {"use_sim_time": LaunchConfiguration("use_sim_time")}
        ],
    )

    # 5. RViz2 시각화 노드 설정
    # 패키지 내부의 rviz 설정 파일을 안전하게 추적
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
            {"use_sim_time": LaunchConfiguration("use_sim_time")}
        ],
    )

    # 6. Static Transform Publisher (World -> Base_link)
    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_publisher",
        output="screen",
        arguments=["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "world", "base_link"],
    )
    
    
    #가상 데모 (RViz에서만 구동하는 경우)    
    # 7. ros2_control 노드 추가
    # 7.1. ros2_controllers.yaml 파일의 절대 경로를 안전하게 추적
    ros2_controllers_path = os.path.join(
        FindPackageShare("my_robot_moveit_config").find("my_robot_moveit_config"),
        "config",
        "ros2_controllers.yaml",
    )
    ros2_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        name="controller_manager",  # 매우 중요: YAML 파일의 최상단 namespace와 일치해야 함
        parameters=[
            moveit_config.robot_description,
            # "config/ros2_controllers.yaml" # 실제 ros2_control 설정 파일 경로로 변경 필요
            ros2_controllers_path   # 7.2. 절대 경로로 변경된 설정 파일 주입
            
        ],
        output="screen",
    )

    # 8. 관절 상태 브로드캐스터 Spawner 추가
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    # 9. 암 궤적 컨트롤러 Spawner 추가 (이름은 yaml 설정에 맞게 변경)
    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_group_controller", "-c", "/controller_manager"],
    )

    # return LaunchDescription 리스트에 위 노드들을 모두 추가하세요.
    

    return LaunchDescription(
        [
            sim_arg,
            static_tf,
            robot_state_publisher_node,
            run_move_group_node,
            rviz_node,
            #가상 데모 (RViz에서만 구동하는 경우)
            ros2_control_node,
            joint_state_broadcaster_spawner,
            arm_controller_spawner,
        ]
    )