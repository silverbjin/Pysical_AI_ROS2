# Ch06 §6.6 — 실제 MoveItPy → Gazebo Harmonic 통합 경로 (CI 인수 가이드)

> 기존 [LAB_6_6_GUIDE_KO.md](LAB_6_6_GUIDE_KO.md)는 Gazebo 물리·컨트롤러 단독 연결을 다룬다.
> 이 추가 실습은 **MoveItPy 계획 → GazeboSimSystem 실제 액션 실행 → 실제 관절 피드백**의 누락된 경계만 검수한다.
> ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic, **시뮬레이션 전용**. 실물 로봇 금지.

## 학습 목표

1. MoveItPy가 OMPL로 경로를 생성하는 과정을 확인한다.
2. 그 궤적이 실제 Gazebo의 gz_ros2_control/GazeboSimSystem으로 전달되어 실행되는지 확인한다.
3. 단순 Goal 수락과 컨트롤러 SUCCEEDED, 관절 피드백 실측 PASS의 차이를 이해한다.
4. 실습 결과를 소스 SHA·CI run·Artifact와 함께 보존한다.

## 사전 조건

- 기존 §6.4 named-ready 및 Pose IK, §6.5 Pilz LIN, §6.6 Gazebo 컨트롤러 단독 동작은 이미 독립적으로 PASS되었다. 다시 반복하지 않는다.
- 정확한 런치 경로는 Gazebo_moveit.launch.py (대소문자 주의)이며, demo_gazebo.launch.py는 실제 저장소에 없다.
- 기존 Gazebo용 URDF에는 gz_ros2_control/GazeboSimSystem 플러그인이 있어야 한다. FakeSystem으로 성공했다고 주장해서는 안 된다.
- GazeboSimSystem과 arm_group_controller가 active이고 FollowJointTrajectory 서버가 존재해야 한다.
- Gazebo와 MoveItPy가 동일한 설치본 my_robot.ros2_control_gazebo.urdf.xacro 및 시뮬레이션 /clock을 사용해야 한다.

## 빠른 검수 — 공개 CI

저장소의 다음 두 파일이 실제 시나리오를 수행한다.

- .github/workflows/book-ch06-moveit-gazebo-66.yml
- ci/ch06_66_moveit_gazebo_once.sh, ci/ch06_66_moveit_gazebo_probe.py

기존 고정 이미지 digest sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f를 그대로 사용하며, 필요한 MoveIt/Gazebo 패키지만 컨테이너에 임시 설치한다. 검수 과정에서 새 이미지를 빌드하지 않는다.

CI의 핵심 순서는 **Gazebo server-only 시작 → 모델 생성 확인 → 실제 GazeboSimSystem 확인 → 컨트롤러/clock readiness → MoveItPy OMPL named ready 계획 → MoveItPy execute → 5관절 피드백 최대 오차 검사 → 독립 JSON 판정 → 정상 종료**이다.

### 실제 확인한 주요 로그

~~~text
CH06_66_GAZEBO_MOVEIT_SAME_URDF_AND_SIM_CLOCK_CONFIG_PASS
CH06_NAMED_READY_PLANNING_PASS
CH06_MOVEIT_EXECUTION_STATUS=SUCCEEDED
CH06_NAMED_READY_EXECUTION_AND_JOINT_GOAL_PASS max_error_rad=0.04138
CH06_66_MOVEIT_OMPL_PLAN_GAZEBO_ACTION_AND_JOINT_FEEDBACK_PASS max_joint_error_rad=0.041380
CH06_66_MOVEIT_TO_GAZEBO_SCOPED_PASS
CH06_66_INDEPENDENT_MOVEIT_PLAN_TO_REAL_GAZEBO_ACTION_RECEIPT_PASS
CH06_66_SHUTDOWN=ROS_LAUNCH_EXITED_AFTER_SIGTERM
~~~

- 최초 공개 CI [Run #43347410213](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43347410213): 성공.
- 원본 [Artifact #14002561374](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43347410213/artifacts/14002561374).
- **실제 검증 소스 SHA:** a16ed55c253c11c76ba2fdc6cc3e2b587100bd1a.
- 각 관절 최대 목표 오차 0.04138rad, 0.06rad 허용 범위 내.

## WSL2 GUI 실습(별도 현장 인수 필요)

터미널 A:

~~~bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
colcon build --symlink-install --packages-select \
  my_robot_description my_robot_moveit_config my_robot_control
source install/setup.bash
ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py use_sim_time:=true
~~~

터미널 B(새 터미널에서 Jazzy와 Ch06만 source):

~~~bash
ros2 control list_controllers -c /controller_manager
ros2 control list_hardware_components -c /controller_manager
ros2 action list -t | grep follow_joint_trajectory
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
~~~

**예상:** Gazebo와 RViz 창(사용 가능한 WSLg/그래픽 환경에서), active 컨트롤러, GazeboSimSystem 및 실제 시뮬레이션 시각이 확인되어야 한다. GUI 표시 자체는 현재 공개 CI에서 검증되지 않았으므로 현장 WSL2 인수에서 스크린샷으로 확인한다.

실제 Gazebo와 연결된 MoveItPy 실행은 CI의 컨트롤러 소유권·GazeboSimSystem 검사 후에만 허용된다. 별도 Python 프로브를 실제 로봇에 직접 실행하지 않는다. MoveItPy Jazzy 소멸자 문제로 검증된 시뮬레이션에서만 후처리 프로세스 교체 우회를 사용했으며, 정상 종료자가 테스트되었다고 주장하지 않는다.

## 판정 경계

**PASS:** 설치된 Gazebo URDF 동일성, MoveItPy OMPL 실제 경로 계획, 실제 Gazebo 컨트롤러 실행 상태 SUCCEEDED, 5관절 관측 목표 오차 0.06rad 이내, 독립 JSON 검수 및 Launch 종료.

**NOT_RUN:** GUI/RViz 시각 동기, 그리퍼 파지, 물체 조작, 장애물 충돌 및 접촉력, 로봇 실물 동작, MoveItPy C++ 소멸자 정상 종료, Ch10 보행.

Ch10 Issue #123 HOLD와 Ch07 Issue #127 및 Ch11 Issue #130의 기존 열린 이슈 상태는 유지한다.
