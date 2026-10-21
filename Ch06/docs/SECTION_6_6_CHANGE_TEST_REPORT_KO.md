# SECTION 6.6 — Gazebo 통합 런치 수정·정적 테스트 보고서

- 기존 브랜치: `feat/ch06-section-6-6`.
- 주요 변경 파일: `ros2_ws/src/my_robot_moveit_config/launch/Gazebo_moveit.launch.py`.
- 원래 문제: Gazebo/로봇 스폰 완료 이전에 `joint_state_broadcaster`, `arm_group_controller` spawner를 독립적으로 실행함. `/controller_manager`의 플러그인 생성보다 먼저 연결 시도할 가능성이 있음.
- 변경: `RegisterEventHandler(OnProcessExit(target_action=spawn_entity, ...))`로 **로봇 스폰 프로세스 종료 이후**에 두 spawner를 실행하게 했다. 서비스 대기 `--controller-manager-timeout 60` 명시; `/controller_manager` 절대 경로 통일.
- 중요한 한계: `OnProcessExit`은 spawn **성공**을 검증하지 않고 프로세스 종료만 감지한다. 모델 spawn 실패, gz_ros2_control plugin 미기동, ControllerManager 서비스 지연 등은 실제 로그/상태 검사 없이는 **BLOCKED**일 수 있다. 완전한 readiness gate로 주장하지 않는다.
- `Ch06/tests/test_section_6_6.py`: 런치 AST 파싱, spawn 이후 spawner 이벤트, manager timeout, /clock bridge, 중복 ros2_control_node 회피를 검사하는 5개 정적 테스트.
- 원격 소스 키워드·구문 구조 정적 검사는 **PASS**. 실제 Python 컴파일, ROS Launch 실행, Gazebo/MoveIt/Controller runtime: **NOT_RUN**.
- 재실행:
  ```bash
  python3 -m py_compile Ch06/ros2_ws/src/my_robot_moveit_config/launch/Gazebo_moveit.launch.py
  python3 -m unittest discover -s Ch06/tests -p test_section_6_6.py -v
  source /opt/ros/jazzy/setup.bash
  cd Ch06/ros2_ws && colcon build --symlink-install
  source install/setup.bash
  ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py use_sim_time:=true
  # 별도 터미널에서 서비스/센서 확인
  ros2 control list_controllers
  ros2 action list -t
  ros2 topic echo /clock --once
  ros2 topic echo /joint_states --once
  ```
- **TASK_PASS 조건:** controller 두 개 ACTIVE, 액션 서버 응답, joint_states 최신성, TF 정상, 계획·실행 결과와 최종 관절 오차 측정. 런치를 띄운 사실만으로는 미충족.
- 후속 과제: gripper_group_controller가 해당 런치에서 생성되지 않으며, moveit_controllers.yaml의 그리퍼 2관절 계약과 ros2_controllers.yaml 단일 joint 타입 차이 해결 필요. Ch05 영향 및 MoveItPy 별도 프로세스의 sim_time 파라미터 검증 필요.
