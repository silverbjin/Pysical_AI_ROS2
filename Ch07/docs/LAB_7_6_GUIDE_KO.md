# Ch07 §7.6 — Gazebo 그리퍼 액션: 두 손가락 관절 열기·닫기

> Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic. 시뮬레이션 전용. 실제 물체 파지 및 리프트는 이번 검수에서 **NOT_RUN**이며, 컨트롤러 동작만 PASS 후보이다.

## 목표

실습의 출발점은 실제 robot 모델의 joint_finger1, joint_finger2 두 **prismatic 관절**이다. 값의 단위는 **m**이며 rad이 아니다. 두 손가락은 서로 반대 축을 따라 움직이고, 각 관절의 URDF 유효 범위는 0.000~0.025m이다.

- 열기(open): 각 관절 0.005m
- 닫기(close): 각 관절 0.020m
- Action: /gripper_group_controller/follow_joint_trajectory (control_msgs/action/FollowJointTrajectory)
- 실제 컨트롤러: gz_ros2_control/GazeboSimSystem 및 vision_basics/config/ros2_controllers.yaml에 정의된 JointTrajectoryController.
- 기존 my_robot_moveit_config/config/ros2_controllers.yaml의 parallel_gripper_action_controller 타입은 이번 실제 시뮬레이터에 사용하지 않는다. 혼용하지 말 것.

중요: **open Action SUCCEEDED → 실제 /joint_states 목표 위치 도달 → close Action SUCCEEDED → 실제 위치 도달** 순서가 맞아야 한다. 과거 원본처럼 비동기 goal만 보내고 spin 이전에 sleep 후 다음 goal을 보내면 완료가 보장되지 않는다.

## 1. 환경과 가상 모델 — 터미널 A

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
sudo apt-get install -y ros-jazzy-gz-ros2-control \
  ros-jazzy-joint-trajectory-controller \
  ros-jazzy-joint-state-broadcaster
colcon build --symlink-install --packages-select vision_basics
source install/setup.bash
ros2 pkg executables vision_basics | grep gripper_controller
xacro "$(ros2 pkg prefix --share vision_basics)/urdf/my_robot.gripper_gazebo.urdf.xacro" \
  > /tmp/ch07_76_gripper.urdf
grep -n 'GazeboSimSystem\|joint_finger1\|joint_finger2' /tmp/ch07_76_gripper.urdf
~~~

독립 wrapper Xacro는 Ch07의 기존 로봇 URDF, 기존 GazeboSimSystem Xacro 및 vision_basics의 그리퍼 JointTrajectoryController 설정을 재사용한다. 이전에 주석 처리된 플러그인 호출을 원본 모델 전체에서 임의로 풀지 않는다.

## 2. 실제 Gazebo 헤드리스 검수 — 공개 GitHub Actions

워크플로: .github/workflows/book-ch07-76-gripper.yml
실행기: ci/ch07_76_gripper_once.sh
독립 관측기: ci/ch07_76_gripper_witness.py

기존 고정 GHCR Jazzy/Harmonic digest sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f를 그대로 사용하며, 임시 Gazebo control 패키지만 설치한다. 기존 Gazebo empty.sdf에서 Ch07 로봇을 소환하고 실제 GazeboSimSystem 플러그인과 컨트롤러를 확인한다.

이 검수는 새로운 월드, 새 Docker 이미지, 실제 카메라, MoveIt 계획, 장애물 또는 물체 파지를 실행하지 않는다.

### 실습 진단 — ROS/Gazebo가 실행된 터미널 B

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws && source install/setup.bash

ros2 control list_hardware_components -c /controller_manager
ros2 control list_controllers -c /controller_manager
ros2 action list -t | grep gripper
ros2 topic echo /joint_states --once
~~~

**예상:** GazeboSimSystem이 실제로 존재, broadcaster 및 gripper_group_controller가 active, 그리퍼 FollowJointTrajectory action server와 2개 finger joint state 존재. Mock FakeSystem이면 이번 Gazebo 실물리 컨트롤러 시험으로 인정하지 않는다.

### 실행 명령 — 별도 터미널 C

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch07/ros2_ws
source install/setup.bash
ros2 run vision_basics gripper_controller
~~~

실제 순서대로 전송하고 Goal accepted, result SUCCEEDED/error_code==0, /joint_states의 각 손가락 목표 오차 0.003m 이내를 모두 확인한다. close에서 실제 관절 변화 0.010m 이상을 요구한다.

정상 로그 예상(실제 성공 주장 전에는 CI 로그에서 확인):

~~~text
CH07_76_REAL_JOINT_STATE_STREAM_READY
CH07_76_OPEN_ACTION_AND_MEASURED_JOINTS_PASS ...
CH07_76_CLOSE_ACTION_AND_MEASURED_JOINTS_PASS ...
CH07_76_SEQUENCE_OPEN_RESULT_THEN_CLOSE_REAL_FEEDBACK_PASS
CH07_76_INDEPENDENT_REAL_GAZEBO_FINGER_ACTION_AND_FINAL_JOINTS_PASS
~~~

실습이 끝나면 터미널 C가 정상 반환한다. Gazebo/RSP/bridge 터미널 A는 별도 종료한다. 공개 CI의 로그·JSON과 종료 상태는 병합 전에 반드시 확인한다.

## 증거 및 경계

- PASS 후보: 실 GazeboSimSystem, 두 prismatic JointTrajectoryController 활성화, open/close 각 Action SUCCEEDED 및 실측 JointState, 독립 최종 위치 측정, 정상 종료.
- NOT_RUN: 실제 물체에 대한 접촉, 마찰 파라미터 최적화, 물체 파지·리프트, MoveIt 그리퍼 통합, 실물 로봇, WSLg GUI 영상.
- Ch07 §7.2 실제 RGB-D renderer Issue #127: BLOCKED 유지.
- Ch11 SaveMap 서비스 Issue #130: FAIL 유지(대체 Nav2 CLI PASS).
- Ch10 Issue #123: HOLD 유지.

그리퍼 Action이 성공했다고 실제 물체를 잡았다고 보고하지 않는다.


## 2026-11-13 공개 CI 실제 인수 기록 및 재검 원칙

> **Ch07 §7.6 실제 Gazebo 그리퍼 제어: 두 CI 증거를 결합한 범위 한정 PASS**. 실제 물체 파지/접촉/리프트는 NOT_RUN.
> 상세 원인과 SHA는 [SECTION_7_6_REPORT_KO.md](SECTION_7_6_REPORT_KO.md)를 참고한다.

- 실제 OPEN/CLOSE Goal과 관절 피드백을 확인한 [CI #43354355284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354355284)에서는 기능이 성공했지만, 종료 스크립트 무한 반복으로 전체 Job이 FAIL이었다. **절대로 해당 Job을 CI 전체 PASS로 표현하지 않는다.**
- 하위 Bash 함수의 루프 변수 \`i\`가 호출자 \`cleanup()\`의 \`i\`를 덮어쓰는 동적 스코프 오류를 \`local attempt\`로 수정했다.
- 이후 [종료 전용 CI #43358805356](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358805356)는 세 소유 프로세스 그룹을 SIGTERM으로 각각 한 번씩 회수했으며 \`result.json\`에서 \`rc=0\`, \`TEARDOWN_SCOPE_PASS\`, \`action_retest=NOT_RUN\`을 확인했다.
- 두 버전의 \`gripper_controller.py\`는 동일한 blob SHA \`1c104193f29940ba565cc3a32cd35c5bf4e51f38\`이다. 성공한 OPEN/CLOSE는 재실행하지 않았다.
- **CI 모드:** 향후 그리퍼 소스/로봇 wrapper/검수기가 변경된 PR에서 전체 OPEN/CLOSE를 실행한다. 종료만 다시 분석할 경우 GitHub Actions의 \`Book Ch07 7.6 real Gazebo two-finger motion\`에서 **Run workflow → scope=teardown_only**를 선택한다. \`full\`은 실제 두 Goal 실행이다. 두 모드는 겹치는 증거를 생성하지 않는다.
- 실습에서 실제 물체가 잡혔는지 확인하려면 손가락 관절 수치 외에 물체 pose, 접촉 및 리프트 증거가 필요하다. 이번 절의 범위 한정 PASS로 물리 파지를 승인하지 않는다.
