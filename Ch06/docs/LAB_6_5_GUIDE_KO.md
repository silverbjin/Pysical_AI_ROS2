# Ch06 §6.5 — Pilz LIN: 사각형 직선 경로의 실제 실행과 검수

> ROS 2 Jazzy / Ubuntu 24.04 / MoveItPy / ros2_control 가상 하드웨어.
> 기존 Ch06 §6.4의 named ready와 Pose IK PASS는 보존하고 재실행하지 않는다.

## 학습 목표

1. 목표에 도달한 것과 말단이 직선으로 이동했다는 주장을 구별한다.
2. Pilz PTP 준비 이동과 Pilz LIN 직선 이동의 역할을 이해한다.
3. X-Z 평면의 **한 변 4cm** 사각형을 네 개의 독립 LIN 구간으로 실행한다. 하나의 블렌딩된 연속 경로라고 주장하지 않는다.
4. 계획 궤적 FK의 직선도와 실제 /joint_states 샘플 FK의 직선도를 서로 독립 판정한다.

## 기존 코드에서 확인한 결함과 수정

기존 cartesian_path.py는 존재하지 않는 설치본 URDF 파일을 참조했고, Pilz 플러그인 설정과 Cartesian limit 확인이 없었으며, 임의의 큰 Pose를 사용했다. 40cm X-Z 경로를 10cm Y-Z라고 표시했고, 실행 상태 검사 없이 os._exit(0)으로 종료했다.

이번 최소 수정에서는 설치된 Ch06 Xacro/SRDF를 재사용한다. 준비 위치는 실제 MoveIt RobotState FK로 생성한 유효한 Pose를 사용한다. 작은 X-Z 사각형을 안전한 가상 컨트롤러에서만 검수한다.

- 준비 PTP: 현재 5개 관절을 읽고, 별도로 정의된 유효 관절 seed의 FK Pose로 이동한다.
- LIN 네 구간: Z -0.04m → X +0.04m → Z +0.04m → X -0.04m. 각 이동 전에 실제 관절 피드백을 기준으로 새 목표를 정한다.
- 각 구간 계획 직선 편차 상한 0.012m, 실측 관절 FK 직선 편차 상한 0.025m, 말단 목표 위치 오차 상한 0.03m, 방향 오차 상한 0.10rad.
- 마지막 위치와 시작 위치 폐합 오차 상한 0.03m. 각 구간은 planning PASS, actual controller SUCCEEDED, 실제 FK 측정 PASS가 모두 필요하다.
- 실제 로봇, Gazebo 물리, 임의의 6D Pose 목표, 40cm 경로, 정상 MoveItPy 소멸자 종료는 이번 범위에서 제외한다.

## 준비 — 터미널 A

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
sudo apt-get install -y ros-jazzy-pilz-industrial-motion-planner

colcon build --symlink-install --packages-select \
  my_robot_description my_robot_moveit_config my_robot_control
source install/setup.bash
ros2 pkg prefix my_robot_description
ros2 pkg prefix my_robot_moveit_config
ros2 pkg prefix pilz_industrial_motion_planner
~~~

**예상:** Ch06 install 경로, Pilz 플러그인 패키지 경로가 모두 조회된다. 이는 준비 검사이며 계획/동작 합격은 아니다.

같은 터미널 A에서 다음 가상 컨트롤러 런치를 실행하고 종료 때까지 유지한다.

~~~bash
ros2 launch my_robot_moveit_config moveit_64_headless.launch.py
~~~

이 런치는 Gazebo/RViz를 열지 않는다. ros2_control 가상 하드웨어의 FollowJointTrajectory 액션을 제공한다.

## 확인 — 새 터미널 B

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
source install/setup.bash

ros2 control list_controllers -c /controller_manager
ros2 control list_hardware_components -c /controller_manager
ros2 action list -t | grep follow_joint_trajectory
ros2 topic echo /joint_states --once
~~~

**예상:** joint_state_broadcaster와 arm_group_controller가 active이고, 실제 하드웨어가 FakeSystem으로 표시된다. 실제 /joint_states와 /arm_group_controller/follow_joint_trajectory 액션도 존재한다. FakeSystem이 확인되지 않으면 실행하지 않는다.

## 시연 — 터미널 B

아래 변수는 컨트롤러가 FakeSystem임을 위 명령으로 확인한 **가상 하드웨어 전용**이다. MoveItPy Jazzy 상위 이슈 moveit/moveit2#3721의 소멸자 오류 때문에, 모든 실행 및 FK 검증·JSON 저장이 끝난 경우에만 이전 Ch06 §6.4와 동일한 명시적 프로세스 교체 우회를 사용한다.

~~~bash
CH06_CI_MOCK_CONTROLLER_VERIFIED=1 \
CH06_CI_RESULT_RECEIPT="$PWD/ch06_65_cartesian_receipt.json" \
python3 -m my_robot_control.cartesian_path --ci-mock-verified-exit

echo "exit=$?"
python3 -m json.tool "$PWD/ch06_65_cartesian_receipt.json"
~~~

### 기대하는 단계별 출력

~~~text
CH06_65_PILZ_CONFIG_AND_CARTESIAN_LIMITS_PASS
CH06_65_FRESH_JOINT_STREAM_PASS ...
CH06_65_PILZ_PTP_PREPOSITION_PLANNING_PASS
CH06_65_PTP_POSITIONING_EXECUTION_AND_FK_PASS
CH06_65_LIN_PLANNED_PATH_PASS segment=1 ...
CH06_65_LIN_EXECUTION_AND_MEASURED_PATH_PASS segment=1 ...
... segment=2,3,4 ...
CH06_65_FOUR_SEGMENT_CLOSED_PATH_PASS ...
CH06_65_PILZ_LIN_FULL_SCOPED_PASS_MOCK_ONLY
exit=0
~~~

**중요:** 이것은 기대 로그 패턴이다. 실제 PASS는 공개 CI에서 위의 로그/JSON/종료코드를 모두 확인해야 한다. plan만 성공하고 execute 또는 실제 FK가 실패하면 FAIL이다. 원본 로그가 없으면 NOT_RUN, 외부 의존성 미비는 BLOCKED로 기록한다.

종료: 터미널 A에서 Ctrl+C 후 터미널 B를 닫는다. 예상 범위를 넘는 SIGKILL 종료는 통과하지 않는다.

## CI 증거와 검수 범위

- 원본 교재 명령: python3 -m my_robot_control.cartesian_path (명시적 mock verified 옵션 필수).
- 전용 공개 workflow: .github/workflows/book-ch06-cartesian-lin.yml
- 검수기: ci/ch06_cartesian_lin_once.sh
- 기존 GHCR digest sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f를 그대로 사용하고 Pilz plugin만 임시 설치한다.
- Evidence: 소스 SHA, 설치 버전, 컨트롤러/액션 상태, 4개 planned/observed 직선도, 실제 실행 상태, 종료 결과, 검증 영수증.
- Ch10 HOLD, Ch07·Ch11의 기존 이슈는 변경하지 않는다.

[이전 정적 리뷰](SECTION_6_5_REPORT_KO.md)에는 과거 원본 코드의 알려진 결함이 기록되어 있다. 새로운 공개 CI 로그가 실제 성공을 증명할 때만 본 절의 scoped PASS를 선언한다.
