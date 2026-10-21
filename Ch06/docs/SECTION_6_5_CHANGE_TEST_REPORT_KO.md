# SECTION 6.5 — Pilz Cartesian LIN 코드 수정 및 정적 테스트 보고서

- 브랜치: `feat/ch06-section-6-5`. 기본 `cartesian_path.py`를 저장소 원고와 대조해 개정.
- 수정: 존재하지 않는 MoveIt config `urdf/` 경로 제거→설치된 `my_robot_description/urdf/my_robot.urdf.xacro` 참조. Pilz planner 명시 YAML을 새로 제공하고 MoveItPy 파라미터에서 `pilz_industrial_motion_planner` 로딩을 검사.
- 이동량을 X-Z 평면 **10cm × 10cm**로 정확히 구현(`--size 0.1`; 과거 코드는 40cm, 설명은 10cm였다). `square_offsets`는 네 변의 상대 이동량을 순서대로 반환.
- 안전 게이트: 기본 모드는 **첫 번째 구간 LIN 계획만 수행**하여 실행 중 상태와 계획상 목표를 혼동하지 않는다. `--execute`로 검증된 mock/Gazebo에서 명시적으로 실행한 경우에만 4구간 순차 plan→execute. 실패한 구간에서 즉시 정지.
- API 차이: 본 예제는 `compute_cartesian_path`가 아닌 **Pilz LIN**. 따라서 `eef_step/jump_threshold/fraction` API를 사용하지 않는다. `jump_threshold=0.0`을 안전한 설정으로 소개하지 않는다.
- 테스트: `tests/test_section_6_5.py`의 AST parse·실행 opt-in·Pilz 플러그인·사각형 폐곡선 구조·강제종료/점프 임계값 허위설명 검사 5종 정의 및 원격 정적 문자열 계약 확인 PASS.
- CPython compile·unittest·Pilz plugin ROS 구동/실제 Cartesian 직선도: **NOT_RUN**. 실제 실행 결과가 없으므로 TASK_PASS 아님.
- 재현 명령:
  ```bash
  python3 -m py_compile Ch06/ros2_ws/src/my_robot_control/my_robot_control/cartesian_path.py
  python3 -m unittest discover -s Ch06/tests -p test_section_6_5.py -v
  source /opt/ros/jazzy/setup.bash
  cd Ch06/ros2_ws && colcon build --symlink-install --packages-up-to my_robot_control
  source install/setup.bash
  ros2 launch my_robot_moveit_config Rviz_Demo.launch.py
  # 별도 터미널(source 이후)
  python3 -m my_robot_control.cartesian_path
  ```
- 미해결: 5축 구성에서 선분 전체의 위치+자세 제약을 만족하는지 불명; Pilz 지원/limits와 controller readiness, joint trajectory 상의 FK 직선도·충돌·관절 급변량 실측 필요. 안전 확인 전 실제 하드웨어 적용 금지.
