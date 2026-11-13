# Ch06 §6.4 — MoveItPy 경로 계획과 실제 컨트롤러 실행

> 대상: ROS 2 Jazzy / Ubuntu 24.04. 최초 구현에는 MoveItPy가 존재하지 않는 `my_robot_moveit_config/urdf/my_robot.urdf`를 읽는 차단 결함이 있었다. 이번 최소 수정은 기존 RViz Launch와 동일한 `my_robot_description/urdf/my_robot.ros2_control_rviz.urdf.xacro`를 사용한다. **Headless fake ros2_control 실행은 Gazebo 물리/실물 로봇 실행이 아니다.**

## 실습 목표와 성공 기준

1. 실제 설치된 Xacro/URDF+SRDF를 일관되게 읽는다. 동일 로봇 이름 `my_robot`, `arm_group` 5개 관절, SRDF named `ready`를 확인한다.
2. `controller_manager`, `joint_state_broadcaster`, `arm_group_controller`가 활성 상태이고 실제 FollowJointTrajectory action 서버가 존재한다.
3. `ros2 run my_robot_control hello_node`로 MoveItPy의 `ready` 동작을 **계획**, 실제 가상 컨트롤러로 **실행**하고, 응답 `ExecutionStatus=SUCCEEDED`와 `/joint_states` 5관절의 목표 오차 `<=0.06 rad`를 확인한다.
4. `MoveItPy.plan()`의 성공만으로 실제 관절 동작 PASS를 선언하지 않는다. 명령 실패·센서 미수신·동작 미달이면 비영(非0) 종료코드가 발생한다.

**정확한 목표**: `joint1=0`, `joint2=0`, `joint3=1.5708`, `joint4=0`, `joint_wrist=0` rad. 실제 joint3가 0에서 약 1.57 rad로 움직여야 한다.

## 1. 설치 및 독립 빌드

아래 터미널은 Ch06 workspace만 source한다. 사용자 PC는 ROS 2 Jazzy, MoveItPy, MoveItConfigsUtils, ros2_control, joint_trajectory_controller, joint_state_broadcaster, mock_components 플러그인이 선행 설치되어야 한다.

터미널 A:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-select \
  my_robot_description my_robot_moveit_config my_robot_control
source install/setup.bash
ros2 pkg prefix my_robot_description
ros2 pkg prefix my_robot_moveit_config
ros2 pkg executables my_robot_control
```

**예상:** 설치 경로가 모두 Ch06 `install/`이고 실행 목록에 `my_robot_control hello_node`가 나온다. `rosdep` 실행만으로 모든 MoveIt/ros2_control 플러그인이 설치되었는지 보장할 수 없으므로 `ros2 pkg prefix moveit_py`, `ros2 pkg prefix controller_manager`도 확인한다.

## 2. Headless 가상 하드웨어 기동 (터미널 A 유지)

```bash
ros2 launch my_robot_moveit_config moveit_64_headless.launch.py
```

이 Launch는 로봇 설명과 `ros2_control`의 `mock_components/GenericSystem`을 사용한다. 실제 Gazebo/RViz 화면을 열지 않는다. **이 터미널은 실습 종료까지 유지**한다.

터미널 B:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
source install/setup.bash
ros2 control list_controllers -c /controller_manager
ros2 control list_hardware_components -c /controller_manager
ros2 action list -t | grep follow_joint_trajectory
ros2 topic echo /joint_states --once
```

**예상:** `joint_state_broadcaster`, `arm_group_controller`가 `active`. `/arm_group_controller/follow_joint_trajectory [control_msgs/action/FollowJointTrajectory]`와 유효한 `/joint_states` 메시지가 나타난다. 준비되지 않았다면 다음 명령을 실행하지 않는다.

## 3. 실제 MoveItPy 계획·실행·검증 (터미널 B)

MoveItPy **Jazzy 2.12.4는 실행 완료 후 객체 소멸 단계에서 SIGSEGV를 일으키는 알려진 상위 결함** ([MoveIt 2 #3721](https://github.com/moveit/moveit2/issues/3721))이 있습니다. 이는 `execute`에서의 궤적 실패와 다른 문제입니다. 정상 소멸자 동작을 검증했다고 주장하지 않습니다.

이 실습은 **반드시 `list_hardware_components` 출력이 `FakeSystem`인 가상 하드웨어에서만**, 검증된 관절 실행이 끝난 후 프로세스를 명시적으로 교체하는 우회를 사용합니다. 실제 로봇에 적용하지 마세요.

```bash
# 터미널 B — 위 단계에서 FakeSystem과 active 컨트롤러를 확인한 후에만 실행
CH06_CI_MOCK_CONTROLLER_VERIFIED=1 \
CH06_CI_RESULT_RECEIPT="$PWD/ch06_64_verified_mock.json" \
ros2 run my_robot_control hello_node --mode named --ci-mock-verified-exit

echo "exit=$?"
python3 -m json.tool "$PWD/ch06_64_verified_mock.json"
ros2 topic echo /joint_states --once
```

**정상 시 기대 로그 순서**:

```text
CH06_MODEL_CONFIG_PASS ...
CH06_JOINT_STATES_READY ...
CH06_NAMED_READY_PLANNING_PASS
CH06_MOVEIT_EXECUTION_STATUS=SUCCEEDED
CH06_NAMED_READY_EXECUTION_AND_JOINT_GOAL_PASS max_error_rad=...
CH06_64_NAMED_READY_COMPLETE_POSE_IK_NOT_RUN
CH06_MOVEITPY_UPSTREAM_3721_TEARDOWN_BYPASSED_AFTER_VERIFIED_MOCK_EXECUTION
exit=0
```

`Planning PASS`만 출력되거나 `Execute SUCCEEDED`인데도 관절 목표 오차가 기준보다 크다면 **미완료/FAIL**이다. 최초 장치 상태에 따라 동작 거리는 달라질 수 있다. `STAGE`별 원인 확인에 사용한다.

## 4. 포즈 IK는 별도 실습

기존 `hello_moveit.py`에는 `(x,y,z)=(0,0,2.1)`, 단위 방향 quaternion을 사용하는 5축 팔의 **경계/특이자세 목표**가 있었지만, 성공을 보장할 수 없었고 실행 상태도 무조건 성공 출력했다. 이번 검증은 `ready` named **5관절 실제 궤적 실행까지**만 포함한다. 포즈 IK는 도달 가능한 위치·orientation·관절 한계와 FK 오차를 검증한 뒤 별도 시험으로 진행한다. `--mode named` 외의 모드는 의도적으로 허용하지 않는다.

## 5. 종료·판정 경계

실습 종료 시 터미널 A의 Launch를 `Ctrl+C`로 종료하고, 터미널 B는 작업을 마친 후 닫는다. 우회 모드는 검증 성공 JSON을 디스크에 먼저 기록한 후 MoveItPy C++ 객체의 문제가 알려진 소멸자 경로를 **실행하지 않는 방식**이며, `exit=0`은 **가상 컨트롤러의 계획·실행·관절 피드백 검수**를 나타낼 뿐 MoveItCpp 정상 종료나 실물 시스템 안전을 보증하지 않는다. 우회 옵션이 없는 기본 실행에서 SIGSEGV가 재현될 수 있으며 이것을 임의의 예외 처리로 숨겨서는 안 된다.

우회 모드에서 계획·실행·관절 도달 어느 하나라도 실패하면 JSON 성공 증거가 기록되지 않으며, 이때는 PASS가 아니다. CI는 로그 세 항목, 실제 컨트롤러 상태, JSON 5관절 오차와 종료 코드를 **독립적으로 교차 확인**한다.

**공개 CI 성공 범위**: 실제 ROS 2 Jazzy·MoveItPy 및 fake ros2_control에서 모델 로드→계획→FollowJointTrajectory→관절 목표값까지 검증한다. Gazebo 물리 시뮬레이션, 실제 로봇 하드웨어, RViz GUI, 물체 파지, 포즈 IK는 **NOT_RUN**이다.

[기존 문제 #126](https://github.com/silverbjin/Pysical_AI_ROS2/issues/126) · [실행 검수 PR #133](https://github.com/silverbjin/Pysical_AI_ROS2/pull/133)

**2026-11-13 공개 CI:** [실제 성공 run #43337790267](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43337790267)에서 named `ready` 계획 및 컨트롤러 `SUCCEEDED`, 최대 관절 오차 **0.005494rad**를 측정했다. 정상 MoveItCpp destructor / Gazebo 물리 / 포즈 IK / WSL2 GUI는 **NOT_RUN**. 최신 재검/셧다운 상태는 해당 PR의 마지막 Actions Artifact를 기준으로 판단한다.


## 6. Pose IK 추가 검수 — FK에서 생성한 도달 가능한 단일 목표 (Issue #134)

**기존 1~5절의 named `ready` 성공 결과는 다시 실행하지 않는다.** 별도 CLI `pose_ik_node`는 임의의 6차원 목표를 추측하지 않고, 설치된 MoveIt `RobotState`에 다음 유효한 5관절 각도를 넣어 `link_wrist`의 FK Pose를 만든다.

- FK seed: `joint1=0.25`, `joint2=-0.25`, `joint3=0.95`, `joint4=0.20`, `joint_wrist=-0.15` rad. 각도는 현재 URDF의 한계 안이며, 절대 Cartesian 목표를 임의로 하드코딩하지 않는다.
- `world` 좌표계의 `PoseStamped`를 `arm_group.set_goal_state(pose_stamped_msg=..., pose_link="link_wrist")`로 전달한다.
- 실제 MoveItPy OMPL `plan()`과 가상 `FollowJointTrajectory` `SUCCEEDED`를 요구한다.
- 실행 후 **새로 관측한** `/joint_states`를 다시 MoveIt `RobotState`에 넣어 FK를 독립 계산한다. Position 오차 `<=0.03m`, quaternion 각도 오차 `<=0.10rad`, 초기 대비 실제 관절 이동 `>=0.10rad`, 초기 Pose와 목표 위치 차 `>=0.08m`를 모두 요구한다.
- 이 목표에서 성공하더라도 **5축 로봇에 대한 임의의 6D Pose IK 일반 성공은 주장하지 않는다.**

### 실행 절차

터미널 A에서 기존 2절의 `moveit_64_headless.launch.py`를 실행하고 유지한다. 이 터미널은 **반드시 가상 `FakeSystem`**이어야 하며 Gazebo 또는 실물 로봇은 허용하지 않는다. 새 터미널 B에서는 환경을 source하고 먼저 컨트롤러 및 가상 하드웨어를 확인한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
source install/setup.bash

ros2 control list_hardware_components -c /controller_manager # FakeSystem 확인
ros2 control list_controllers -c /controller_manager # 2개 active 확인
ros2 action list -t | grep follow_joint_trajectory
ros2 pkg executables my_robot_control | grep pose_ik_node
```

위 실제 출력으로 `FakeSystem`을 확인하지 못했다면 다음 코드를 **실행하지 않는다**. 확인이 끝난 터미널 B에서만:

```bash
CH06_CI_MOCK_CONTROLLER_VERIFIED=1 \
CH06_CI_RESULT_RECEIPT="$PWD/ch06_64_pose_receipt.json" \
ros2 run my_robot_control pose_ik_node --ci-mock-verified-exit

echo "exit=$?"
python3 -m json.tool "$PWD/ch06_64_pose_receipt.json"
```

기대하는 주요 로그 순서(실제 PASS 여부는 로그와 JSON/관절 데이터를 교차 확인):

```text
CH06_POSE_JOINT_STREAM_READY ...
CH06_POSE_FK_TARGET_CREATED ...
CH06_POSE_IK_GOAL_ACCEPTED
CH06_POSE_IK_PLANNING_PASS
CH06_POSE_IK_EXECUTION_STATUS=SUCCEEDED
CH06_POSE_IK_EXECUTION_FK_FEEDBACK_PASS ...
CH06_POSE_IK_SCOPED_PASS_MOCK_ONLY
CH06_POSE_UPSTREAM_3721_TEARDOWN_BYPASSED_AFTER_FK_PASS
exit=0
```

`Planning PASS`만 나오거나, 실행 상태가 `SUCCEEDED`이더라도 **실측 FK 위치·방향 잔차가 기준 초과**라면 Pose IK는 FAIL이다. JSON 증거 없이 종료코드만 0이라면 성공으로 처리하지 않는다. `--ci-mock-verified-exit`는 기존 [MoveIt 2 #3721](https://github.com/moveit/moveit2/issues/3721) 소멸자 문제를 피하기 위한 **가상 컨트롤러 전용 우회**이며 정상 destructor 종료는 **NOT_RUN**이다.

[Issue #134](https://github.com/silverbjin/Pysical_AI_ROS2/issues/134) · 공개 CI `.github/workflows/book-ch06-pose-ik.yml`. 이 절의 실제 CI PASS/FAIL 판정은 해당 PR의 **실행 로그 및 Artifact**를 기준으로 하며, 이전 named-ready run #43338734506의 성공을 재사용하여 Pose IK까지 PASS로 승격하지 않는다. GUI/물리/실물 하드웨어는 계속 NOT_RUN이다.
