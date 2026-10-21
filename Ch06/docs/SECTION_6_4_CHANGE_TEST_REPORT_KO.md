# SECTION 6.4 — MoveItPy 제어 예제 수정 및 정적 테스트 보고서

- 기존 브랜치 `feat/ch06-section-6-4`의 코드/리뷰 결과를 기준으로 한다.
- `hello_moveit.py`: 존재하지 않는 MoveIt config `urdf/` 경로 대신 `my_robot_description/urdf/my_robot.urdf.xacro` 설치본을 사용한다. 필수 파일 존재 검사 추가.
- OMPL 파이프라인·planning scene 파라미터를 명확히 구성하고 5축 팔에 position-only IK 설정을 적용한다. 6D 자세 정확도는 **검증 대상이 아니다**.
- 기본 실행은 **계획만 수행**한다. 사용자가 `--execute`를 명시한 mock/Gazebo 환경에서만 궤적 실행, 반환 상태/실측 FK의 구분 설명.
- named goal=`ready`와 IK XYZ goal=(0.3,0.0,1.1)m를 순차 시험한다. 실제 도달 가능성, 충돌 여부는 런타임에서 별도 검증.
- `os._exit(0)` 강제 종료 제거, 계획 실패별 nonzero 종료코드, `finally`에서 rclpy shutdown. `setup.py`에 `hello_moveit` alias를 추가하되 `hello_node` 보존.
- `Ch06/tests/test_section_6_4.py`: Python AST 적합성·실행 opt-in·올바른 모델/링크 이름·강제 종료 제거·허위 실행성공 로그 제거 (5항목).
- 소스 구조/안전 계약에 대한 점검: **STATIC_REVIEWED / PASS (5항목 선언 확인)**. 독립 CPython/colcon/실제 MoveIt API·controller runtime: **NOT_RUN**.
- 추후 실행:
  ```bash
  python3 -m py_compile Ch06/ros2_ws/src/my_robot_control/my_robot_control/hello_moveit.py
  python3 -m unittest discover -s Ch06/tests -p test_section_6_4.py -v
  source /opt/ros/jazzy/setup.bash
  cd Ch06/ros2_ws && colcon build --symlink-install --packages-up-to my_robot_control
  source install/setup.bash
  ros2 launch my_robot_moveit_config Rviz_Demo.launch.py
  # 별도 터미널: source 후, 컨트롤러 준비를 확인하고 plan-only 실행
  ros2 run my_robot_control hello_moveit
  # 검증된 mock/Gazebo에서만: ros2 run my_robot_control hello_moveit --execute
  ```
- 미해결: `Rviz_Demo.launch.py`가 목표 시간/관절 상태를 안정적으로 공급하는지, 5축 목표 FK 오차, 액션 실행 상태의 문자열 표현은 실제 런타임 검증 필요.
