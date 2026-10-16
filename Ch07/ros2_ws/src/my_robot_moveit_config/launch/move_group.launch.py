from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config").to_moveit_configs()
    return generate_move_group_launch(moveit_config)




# generate_move_group_launch 직접 구현 시도 for 동작 원리 이해
# from launch import LaunchDescription
# from launch.actions import DeclareLaunchArgument
# from launch.substitutions import LaunchConfiguration

# from launch_ros.actions import Node

# from moveit_configs_utils import MoveItConfigsBuilder


# def generate_launch_description():

#     use_sim_time = LaunchConfiguration("use_sim_time")

#     moveit_config = (
#         MoveItConfigsBuilder(
#             "my_robot",
#             package_name="my_robot_moveit_config"
#         )
#         .to_moveit_configs()
#     )

#     move_group_node = Node(
#         package="moveit_ros_move_group",
#         executable="move_group",
#         output="screen",
#         parameters=[
#             moveit_config.to_dict(),
#             {
#                 "use_sim_time": use_sim_time
#             }
#         ],
#     )

#     return LaunchDescription([
#         DeclareLaunchArgument(
#             "use_sim_time",
#             default_value="true"
#         ),
#         move_group_node
#     ])


# launch_arguments={'use_sim_time': use_sim_time}.items(), # not work
# 이유: move_group.launch.py 내부를 보시면 아시겠지만, 이 파일은 전달받은 launch_arguments를 받아 MoveItConfigsBuilder에 전달하는 로직이 빠져있습니다. 빌더는 파이썬 코드 실행 시점에 파라미터를 미리 확정해 버리기 때문에, 외부에서 동적으로 넘겨준 use_sim_time이 move_group 노드까지 도달하지 못하는 것입니다.
# 해결 방안: Gazebo 시뮬레이션 연동 시 이 부분을 해결하려면 move_group.launch.py를 다음과 같이 수정해야 합니다.
# from launch import LaunchDescription
# from launch.actions import DeclareLaunchArgument
# from launch.substitutions import LaunchConfiguration
# from moveit_configs_utils import MoveItConfigsBuilder
# from moveit_configs_utils.launches import generate_move_group_launch

# def generate_launch_description():
#     use_sim_time = LaunchConfiguration('use_sim_time')
    
#     # DeclareLaunchArgument를 통해 외부에서 값을 받을 수 있도록 선언
#     ld = LaunchDescription([
#         DeclareLaunchArgument('use_sim_time', default_value='false', description='Use sim time')
#     ])

#     # .sim_time() 메서드를 활용하여 빌더에 시뮬레이션 시간 사용 여부 주입 (ROS 2 Humble/Jazzy 기준)
#     moveit_config = (
#         MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
#         .sim_time(use_sim_time) # 이 부분이 핵심입니다
#         .to_moveit_configs()
#     )
    
#     # 생성된 move_group 실행 요소를 LaunchDescription에 추가
#     move_group_node = generate_move_group_launch(moveit_config)
#     ld.add_action(move_group_node)
    
#     return ld




