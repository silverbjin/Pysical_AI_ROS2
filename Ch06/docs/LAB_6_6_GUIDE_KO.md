# Ch06 §6.6 — Gazebo Harmonic × ros2_control × MoveIt 통합 전 단계 검수

> Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic. 이 실습은 시뮬레이션 전용이다. 실제 로봇 하드웨어에서는 실행하지 않는다.
> 앞서 검수한 §6.4 및 §6.5는 보존하며 재검하지 않는다.

## 학습 목표

1. 실제 Gazebo 로봇 엔티티가 생성되고, ros2_control 플러그인이 FakeSystem이 아닌 GazeboSimSystem으로 연결되는지 확인한다.
2. /clock, /joint_states, /controller_manager, /arm_group_controller/follow_joint_trajectory가 하나의 시뮬레이션에서 연결되는지 확인한다.
3. FollowJointTrajectory action 결과와 실제 관절 피드백 및 시각을 기준으로 동작을 판정한다.
4. **컨트롤러-물리 연동 PASS와 MoveIt 전체 통합 PASS를 분리**한다.

## 기존 결함과 이번 최소 교정

기존 Gazebo_moveit.launch.py는 Gazebo 시작, 모델 생성, 컨트롤러 활성화를 모두 동시에 요청하여 startup race가 발생할 수 있었다. 새 버전은 실제 모델 생성 프로세스 종료 후 joint_state_broadcaster를 시작하고, 그 spawner가 종료된 후 arm_group_controller를 시작한다. 각 spawner의 대기 시간도 유한하게 둔다. 성공은 readiness 실제 상태로 확인한다.

동일한 런치에 headless 및 start_rviz 인자를 추가했다. 기존 GUI 시작값은 유지했으며, CI에서만 Gazebo 서버 모드와 RViz 비활성화를 사용한다.

## 환경 구축 — 터미널 A

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select \
  my_robot_description my_robot_moveit_config my_robot_control
source install/setup.bash

ros2 pkg prefix gz_ros2_control
ros2 pkg prefix ros_gz_sim
~~~

필요한 MoveIt 및 Gazebo 관련 패키지는 사전에 설치되어 있어야 한다. 실습 전 다른 Ch의 같은 패키지 overlay를 source하지 않은 새 터미널을 사용한다.

### GUI 시연: 터미널 A 계속 사용

~~~bash
ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py use_sim_time:=true
~~~

**예상:** Gazebo 월드와 로봇, RViz 창, 생성 성공 로그가 나타난다. GPU/WSLg 화면은 CI에서 검수할 수 없으므로 현장 WSL2에서 직접 확인한다. 화면만 떴다고 컨트롤러 동작이 검증된 것은 아니다.

### GUI 없이 동일한 실제 Gazebo 서버 실행

~~~bash
ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py \
  use_sim_time:=true headless:=true start_rviz:=false
~~~

이 명령은 렌더러를 제외하지만 **실제 Gazebo 물리 및 gz_ros2_control 플러그인**은 사용한다. fake ros2_control 전용 §6.4 런치가 아니다.

## 토픽·액션·모델 연결 확인 — 새 터미널 B

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
source install/setup.bash

ros2 control list_controllers -c /controller_manager
ros2 control list_hardware_components -c /controller_manager
ros2 action list -t | grep follow_joint_trajectory
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
~~~

**예상:** 두 컨트롤러가 active, hardware component가 GazeboSimSystem, FollowJointTrajectory 서버 존재, /clock과 /joint_states의 헤더 시각 증가. FakeSystem이라면 **이번 시험을 시작하지 않는다**.

## 실제 Gazebo Action 한 번의 제어 검증 — 터미널 B

이 동작은 시뮬레이션에서 단일 관절의 작은 목표값만 설정한다. MoveIt path planning을 호출하지 않으므로 **최종 MoveIt 통합 시연 PASS가 아니다**.

~~~bash
cd ~/Pysical_AI_ROS2
CH06_66_RECEIPT="$PWD/ch06_66_gazebo_receipt.json" \
python3 ci/ch06_66_gazebo_action_probe.py

echo "exit=$?"
python3 -m json.tool "$PWD/ch06_66_gazebo_receipt.json"
~~~

**정상 시 기대 로그(실제 수치는 동작 후 확인):**

~~~text
CH06_66_SIM_CLOCK_AND_JOINT_STREAM_PASS ...
CH06_66_ACTUAL_GAZEBO_ACTION_SERVER_PASS
CH06_66_GAZEBO_GOAL_ACCEPTED
CH06_66_GAZEBO_FOLLOW_JOINT_TRAJECTORY_SUCCEEDED ...
CH06_66_GAZEBO_JOINT_MOTION_FEEDBACK_PASS ...
CH06_66_CONTROLLER_GAZEBO_SCOPE_PASS_MOVEIT_PLANNING_NOT_RUN
exit=0
~~~

한 번의 Goal accepted만으로 성공이 아니다. result status 성공과 실제 joint3가 0.20rad 이상 변화했고 마지막 목표 오차가 0.08rad 미만이며, /clock 2초 이상 진행, 액션 피드백 1개 이상을 모두 증명해야 한다.

실습 종료 시 터미널 A에서 Ctrl+C로 launch를 정상 종료하고, 터미널 B 작업을 종료한다.

## CI 판정 경계

- 공개 CI: .github/workflows/book-ch06-gazebo-66.yml
- 실행기: ci/ch06_66_gazebo_once.sh
- Source SHA, GHCR 고정 digest, 설치 버전, 생성된 URDF, Launch 원본 로그, 실제 Gazebo hardware, /clock, /joint_states, Action result, 독립 JSON 검증과 shutdown를 증거로 남긴다.
- 이번 성공 가능 범위: **Gazebo 실제 controller/action/관절 피드백 연결**.
- 아직 NOT_RUN: MoveIt 계획을 실제 Gazebo로 전달하는 end-to-end 계획, 그리퍼 동작, GUI 시각 인수, 물체 파지, 실물 로봇, Ch10.
- 이미 검수한 Ch06 §6.4·§6.5는 새로운 CI에서 다시 실행하지 않는다.

[이전 정적 검토](SECTION_6_6_REPORT_KO.md)의 결함 근거는 보존한다. 실제 CI에서 성공한 부분과 아직 검증되지 않은 부분을 분리하여 보고한다.
