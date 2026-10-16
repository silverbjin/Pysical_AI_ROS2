#!/usr/bin/env python3

import rclpy
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder

def main(args=None):
    rclpy.init(args=args)

    print("1. 로봇 설정 파라미터 로드 중...")
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path="config/my_robot.urdf.xacro")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    # MoveItPy(MoveItCpp) 구동에 반드시 필요한 핵심 파라미터들을 강제 주입
    moveit_py_config = moveit_config.to_dict()
    
    # 솔루션: 💡 핵심 파라미터 보강: planning_pipelines와 ompl 플러그인 정보가 누락되는 문제 해결
    moveit_py_config["planning_pipelines"] = {
    "pipeline_names": ["ompl"],
    "default_planning_pipeline": "ompl",
    }
    
    # 1. 사용할 파이프라인 리스트와 플랜 요청 기본값 설정
    moveit_py_config.update({
        "planning_pipelines": ["ompl"],
        "plan_request_params": {
            "planning_attempts": 1,
            "planning_pipeline": "ompl",
            "max_velocity_scaling_factor": 1.0,
            "max_acceleration_scaling_factor": 1.0,
        }
    })
    
    # 2. OMPL 플러그인 정보가 누락되는 것을 방지
    moveit_py_config.setdefault("ompl", {})
    moveit_py_config["ompl"]["planning_plugin"] = "ompl_interface/OMPLPlanner"

    print("2. MoveItPy 노드 초기화 중...")
    # 보강된 파라미터 딕셔너리로 노드 생성
    my_robot = MoveItPy(node_name="moveit_py_client", config_dict=moveit_py_config)
    
    # 로그에서 확인했던 그룹 이름 "arm_group"을 사용합니다.
    arm = my_robot.get_planning_component("arm_group")

    print("3. 로봇 상태 설정 중...")
    # 시작 상태를 현재 로봇의 상태로 동기화
    arm.set_start_state_to_current_state()

    # 목표 상태 설정 
    # 현재 상태 객체를 복사한 뒤, 목표 관절 각도만 덮어씌우는 방식이 가장 안전합니다.
    target_state = my_robot.get_robot_state()
    
    # 주의: 배열의 길이는 "arm_group"에 속한 관절 개수(로그 상 5개)와 정확히 일치해야 합니다. (단위: Radian)
    target_joint_positions = [0.5, -0.5, 0.5, 0.0, 0.0]
    target_state.set_joint_group_positions("arm_group", target_joint_positions)
    
    # SRDF에 "ready"나 "home" 같은 이름이 지정되어 있다면 아래 한 줄로 대체 가능합니다.
    # arm.set_goal_state(configuration_name="ready")
    
    arm.set_goal_state(robot_state=target_state)

    print("4. 경로 계획(Plan) 시작...")
    plan_result = arm.plan()

    # Plan 성공 여부 확인 후 Execute 수행
    if plan_result:
        print("✅ 경로 계획 성공! 컨트롤러로 Execute 명령을 전송합니다.")
        # 생성된 궤적을 ros2_control 액션 서버로 전송합니다.
        my_robot.execute(plan_result.trajectory, controllers=[])
        print("🎉 이동 완료!")
    else:
        print("❌ 경로 계획에 실패했습니다. (목표 지점이 도달 불가능하거나 충돌 발생)")
        


if __name__ == '__main__':
    main()