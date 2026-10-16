#!/usr/bin/env python3
import rclpy
from rclpy.logging import get_logger
from moveit_configs_utils import MoveItConfigsBuilder
from moveit.planning import MoveItPy

# 💡 Bug Fix: 리스트와 튜플 혼용 대신, 딕셔너리 .update()를 사용하여 안전하게 평탄화
def flatten_dict(d, prefix=''):
    items = {}
    for k, v in d.items():
        new_key = f"{prefix}{k}" if prefix else k
        if isinstance(v, dict):
            # 하위 딕셔너리 병합
            items.update(flatten_dict(v, prefix=new_key + '.'))
        else:
            items[new_key] = v
    return items

def main(args=None):
    # 1. ROS 2 통신 컨텍스트 초기화
    rclpy.init(args=args)
    logger = get_logger("moveit_direct_node")
    
    logger.info("=== [my_robot_control] MoveItConfigsBuilder 로드 시작 ===")
    
    # 2. 원격 설정 패키지로부터 MoveIt 설정 빌드
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_robot_moveit_config")
        .robot_description(file_path="config/my_robot.urdf.xacro")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )
    
    logger.info("=== [my_robot_control] MoveItConfigsBuilder 로드 완료 ===")
    
    # ----------------------------------------------------
    # [1단계 디버깅] 오리지널 딕셔너리 데이터 무결성 검사
    # ----------------------------------------------------
    import json
    
    original_dict = moveit_config.to_dict()
    
    print("\n" + "="*40 + " [DEBUG] ORIGINAL DICT STRUCTURE " + "="*40)
    # 읽어온 파라미터 중 planning_pipelines 관련 키만 필터링하여 출력
    pipeline_keys = {k: v for k, v in original_dict.items() if "planning" in k or "ompl" in k}
    print(json.dumps(pipeline_keys, indent=2))
    print("="*113 + "\n")

    # ----------------------------------------------------
    # [2단계 디버깅] 평탄화(Flatten) 데이터 구조 검사
    # ----------------------------------------------------
    flat_config = flatten_dict(original_dict)
    
    print("="*40 + " [DEBUG] FLATTENED DICT STRUCTURE " + "="*40)
    flat_pipeline_keys = {k: v for k, v in flat_config.items() if "planning" in k or "ompl" in k}
    print(json.dumps(flat_pipeline_keys, indent=2))
    print("="*114 + "\n")
    
    

    # 3. 안전하게 수정된 평탄화 함수 적용
    flat_config = flatten_dict(moveit_config.to_dict())    
    # sol. 1: 평탄화 제거 및 오리지널 딕셔너리 직렬화 주입
    config_dict = moveit_config.to_dict()    
    # sol. 2: moveit_cpp 네임스페이스 래핑 (솔루션 1 실패 시 적용)
    raw_dict = moveit_config.to_dict()    
    # MoveItPy 파라미터 서버가 요구하는 네임스페이스 감싸기 대안
    config_dict = {}
    for k, v in raw_dict.items():
        # 플래닝 및 오큐판시 관련 핵심 파라미터를 moveit_cpp 하위로 리맵핑
        if k in ["planning_pipelines", "default_planning_pipeline", "ompl", "trajectory_execution"]:
            if "moveit_cpp" not in config_dict:
                config_dict["moveit_cpp"] = {}
            config_dict["moveit_cpp"][k] = v
        else:
            config_dict[k] = v
    # sol. 3: 전역 ROS 2 파라미터 백엔드 주입 (치트키 워크아라운드)
    # 중요: rclpy.init() 전에 sys.argv에 ROS 2 글로벌 파라미터 인자를 강제로 주입합니다.
    # 이렇게 하면 론치 파일로 파라미터를 넘긴 것과 동일한 효과를 냅니다.
    import sys
    if args is None:
        args = sys.argv
        
    # 명시적으로 파이프라인 플래너 파라미터를 명령행 인자에 추가
    args.extend([
        '--ros-args',
        '-p', 'planning_pipelines:=["ompl"]',
        '-p', 'default_planning_pipeline:="ompl"'
    ])    
    # rclpy.init(args=args)
    logger = get_logger("moveit_direct_node")
        

    try:
        # 4. 평탄화된 딕셔너리를 MoveItPy 네이티브 파라미터로 주입
        # logger.info("Jazzy MoveItPy C++ 엔진 초기화 중 (평탄화 데이터 주입)...")
        logger.info("Jazzy MoveItPy 엔진 구동 (글로벌 파라미터 컨텍스트 이용)...")
        moveit = MoveItPy(
            node_name="moveit_direct_node",
            # config_dict=flat_config
            # config_dict=config_dict # sol. 1: 평탄화 제거 및 오리지널 딕셔너리 직렬화 주입
            # config_dict=config_dict # sol. 2: moveit_cpp 네임스페이스 래핑
            config_dict=moveit_config.to_dict() # sol. 3: 전역 ROS 2 파라미터 백엔드 주입 (치트키 워크아라운드
        )
        
        logger.info("Jazzy MoveIt 제어 인터페이스가 성공적으로 연결되었습니다.")
        
        # 5. 플래닝 컴포넌트(arm_group) 기동
        arm_group = moveit.get_planning_component("arm_group")
        
        logger.info("'home' 위치로 궤적 계획을 시작합니다...")
        arm_group.set_start_state_to_current_state()
        arm_group.set_goal_state(configuration_name="home")
        
        # 6. 계획(Plan) 및 실행(Execute)
        plan_result = arm_group.plan()
        if plan_result:
            logger.info("경로 계획 성공! 로봇을 구동합니다.")
            moveit.execute(plan_result.trajectory, blocking=True)
            logger.info("목표 위치 이동 완료.")
        else:
            logger.error("경로 계획 수립에 실패했습니다. OMPL 설정을 확인하세요.")
            
    except Exception as e:
        logger.error(f"구동 중 런타임 에러 발생: {e}")
        
    rclpy.shutdown()

if __name__ == "__main__":
    main()