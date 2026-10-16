#!/usr/bin/env python3
import time
import os
import gc
import rclpy
import copy
from geometry_msgs.msg import PoseStamped

from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder

def build_cartesian_config():
    moveit_config = (
        MoveItConfigsBuilder(robot_name="my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path="urdf/my_robot.urdf.xacro")
        .robot_description_semantic(file_path="config/my_robot.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )
    
    params = moveit_config.to_dict()

    params["planning_pipelines"] = {
        "pipeline_names": ["ompl", "pilz_industrial_motion_planner"],
        "default_planning_pipeline": "pilz_industrial_motion_planner", 
    }

    params["planning_scene_monitor_options"] = {
        "name": "planning_scene_monitor",
        "robot_description": "robot_description",
        "joint_state_topic": "/joint_states",
        "wait_for_initial_state_timeout": 10.0,
    }

    # 직선 이동(LIN) 설정 및 속도/가속도 제한 (안전 확보)
    params["plan_request_params"] = {
        "planning_pipeline": "pilz_industrial_motion_planner",
        "planner_id": "LIN", 
        "planning_attempts": 3,  # 복잡한 궤적을 위해 시도 횟수 약간 증가
        "planning_time": 5.0,
        "max_velocity_scaling_factor": 0.1,    
        "max_acceleration_scaling_factor": 0.1,
    }
    
    return params

def main():
    rclpy.init()
        
    print("=== MoveItPy Cartesian Square Trajectory ===")
    
    config_dict = build_cartesian_config()
    my_robot = MoveItPy(node_name="cartesian_square_node", config_dict=config_dict)
    arm = my_robot.get_planning_component("arm_group")    
    time.sleep(2.0) # 초기화 대기
    
    # (초기위치) 1. 목표 좌표 생성 (기존 상태나 하드코딩된 안전한 절대 좌표 활용)
    target_pose = PoseStamped()
    target_pose.header.frame_id = "base_link"
    target_pose.pose.position.x = 1.0
    target_pose.pose.position.y = 0.0
    target_pose.pose.position.z = 1.1 # 목표 높이
    target_pose.pose.orientation.x = 0.0
    target_pose.pose.orientation.y = 0.707065
    target_pose.pose.orientation.z = 0.0
    target_pose.pose.orientation.w = 0.707065

    # (초기위치) 2. 목표 설정
    arm.set_start_state_to_current_state()
    arm.set_goal_state(pose_stamped_msg=target_pose, pose_link="link_wrist")
    # arm.set_goal_state(configuration_name="ready")

    # (초기위치) 3. 플래닝 수행 (설정에 의해 자동으로 LIN 데카르트 궤적이 계산됨)
    lin_plan = arm.plan()
    
    if lin_plan:
        print(">> (초기위치) 데카르트 경로(LIN) 계획 성공! 궤적을 실행합니다.")
        my_robot.execute(lin_plan.trajectory, controllers=[])
    else:
        print(">> (초기위치) 데카르트 경로 계획 실패. (특이점 또는 관절 한계 초과 가능성)")

    time.sleep(2.0)
    print("\n=== Tutorial Finished ===")
    

    # ---------------------------------------------------------
    # 1. 현재 위치 읽어오기 (사각형의 시작점)
    # ---------------------------------------------------------
    with my_robot.get_planning_scene_monitor().read_only() as scene:
        robot_state = scene.current_state
        current_pose_msg = robot_state.get_pose("link_wrist") 

    # 이동을 누적할 목표 포즈 객체 초기화
    target_pose = PoseStamped()
    target_pose.header.frame_id = "base_link"
    target_pose.pose = copy.deepcopy(current_pose_msg)

    # ---------------------------------------------------------
    # 2. 사각형 꼭지점 변위(Offsets) 정의 
    # (Y-Z 평면 기준 10cm 크기 사각형)
    # ---------------------------------------------------------
    # 순서: (X, Y, Z) 변위량
    square_moves = [          
        (0.0,  0.0, -0.4), # Waypoint 1: 아래로 0.4m 이동 (-Z)
        (0.4,  0.0, 0.0),  # Waypoint 2: 앞으로 0.4m 이동 (+X)
        (0.0,  0.0, 0.4),  # Waypoint 3: 위로 0.5m 이동 (+Z)
        (-0.4, 0.0, 0.0)   # Waypoint 4: 뒤로 0.5m 이동 (-X, 원위치 복귀)
    ]
    print("\n[사각형 그리기 시작] 10cm 크기의 정방형 궤적을 순차 실행합니다.")

    # ---------------------------------------------------------
    # 3. 궤적 순차 계획 및 실행 (Loop)
    # ---------------------------------------------------------
    for i, (dx, dy, dz) in enumerate(square_moves):
        print(f"\n--> [Waypoint {i+1}] 이동 계획 중... (dx:{dx}, dy:{dy}, dz:{dz})")
        
        # 이전 목표 위치에서 상대 변위만큼 누적
        target_pose.pose.position.x += dx
        target_pose.pose.position.y += dy
        target_pose.pose.position.z += dz

        # 매 이동마다 시작점을 '현재 상태'로 갱신해야 자연스럽게 이어집니다.
        arm.set_start_state_to_current_state()
        arm.set_goal_state(pose_stamped_msg=target_pose, pose_link="link_wrist")

        lin_plan = arm.plan()

        if lin_plan:
            print(f">> Waypoint {i+1} 데카르트 직선(LIN) 계획 성공! 이동합니다.")
            my_robot.execute(lin_plan.trajectory, controllers=[])
            
            # 다음 꼭지점 이동 전 로봇이 완전히 멈추고 Scene 모니터가 동기화될 시간을 줍니다.
            time.sleep(1.0) 
        else:
            print(f">> ⚠️ Waypoint {i+1} 계획 실패! 로봇 팔의 물리적 한계 영역이거나 특이점입니다.")
            break  # 루프 중단

    # ---------------------------------------------------------
    # 4. 프로세스 안전 종료 (Segfault 완벽 차단)
    # ---------------------------------------------------------
    time.sleep(2.0) # 종료 전 대기
    print("\n=== All Trajectories Finished ===")
    
    try:
        del arm
        del my_robot
    except NameError:
        pass

    gc.collect()
    
    rclpy.shutdown()        
    os._exit(0)
        
if __name__ == "__main__":
    main()