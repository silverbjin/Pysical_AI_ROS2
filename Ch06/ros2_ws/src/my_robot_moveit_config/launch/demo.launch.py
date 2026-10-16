import os
from ament_index_python.packages import get_package_share_directory

from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config").to_moveit_configs()
        
    # # 1. Description 패키지 내부에 있는 진본 URDF 파일의 절대 경로를 만듭니다.
    # urdf_path = os.path.join(
    #     get_package_share_directory("my_robot_description"),
    #     "urdf",
    #     "my_robot_control_rviz.urdf.xacro"
    # )

    # # 2. Builder에 .robot_description() 체인을 추가하여 경로를 강제로 덮어씌웁니다.
    # moveit_config = (
    #     MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
    #     .robot_description(file_path=urdf_path)
    #     .to_moveit_configs()
    # )    
   
    return generate_demo_launch(moveit_config)
