# 4.7절 실습 가이드: Gazebo 2축 로봇팔 위치 제어

**실습 범위:** Ch04 원고의 목표는 `joint1`이지만, 현재 repo에서 재사용 가능한 실행 코드는 **Ch03의 `joint2`** 제어기다. 이 차이를 숨기지 않고 `joint2` 제어 실험으로 진행한다.

## 1. 안전·환경

- **Gazebo 시뮬레이션 전용 실습**이다. 로봇 실물에 바로 적용하지 않는다.
- `Ch03/ros2_ws/src/my_robot_description`의 `two_dof_arm.urdf.xacro`, `sim_sync.launch.py`, `joint_control_cli.py`를 사용한다.
- ROS 2 Jazzy/Gazebo Harmonic GUI 지원 터미널, `ros_gz_bridge`가 필요하다.
- 4.6 실습에서 /clock, /joint_states, base_link→link2 TF 연결 여부를 먼저 확인한다. `joint_state_publisher_gui`는 종료한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
colcon build --packages-select my_robot_description --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_description
```

## 2. Gazebo + bridge 실행 (터미널 A)

```bash
ros2 launch my_robot_description sim_sync.launch.py
```

실제 플러그인 `two_dof_arm.urdf.xacro`의 목표 토픽은 `/model/my_robot/joint2/cmd_pos`. Ch03 sim_sync에는 이를 ROS `/joint2/cmd_pos`로 노출하는 브리지가 선언돼 있다. Gazebo와 RViz가 뜬 뒤 spawn 성공과 /joint_states 수신을 먼저 확인한다.

## 3. 메시지·실제 라우팅 확인 (터미널 B)

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch03/ros2_ws/install/setup.bash
ros2 topic list -t | grep -E 'joint|clock'
ros2 topic info /joint2/cmd_pos -v
gz topic -l | grep cmd_pos
ros2 topic echo /joint_states
```

Gazebo의 `gz topic -l`에 나타난 실제 수신 토픽을 확인한다. `ros2 topic info`에 ROS 구독자가 나타나지 않으면 브리지 실행/이름 remap을 확인한다.

## 4. 실제 제어 노드 실행 (터미널 C)

```bash
ros2 run my_robot_description joint_control_cli
```

**예상 로그:** 약 2초마다 `Sending command: -45 degrees`와 `45 degrees`가 반복된다. 실제 메시지 `msg.data`는 ±0.785 rad(≈±45°). `joint2` 관절은 URDF에서 ±1.57 rad 범위다.

노드를 실행하지 않고 한번만 명령을 발행하는 대조 실험:

```bash
ros2 topic pub --once /joint2/cmd_pos std_msgs/msg/Float64 '{data: 0.5}'
ros2 topic pub --once /joint2/cmd_pos std_msgs/msg/Float64 '{data: 0.0}'
```

**중복 명령을 피하도록** 반복 제어 노드를 Ctrl+C로 중지한 다음 수동 명령을 전송한다. 브리지가 준비되지 않았다면 일회성 메시지가 유실될 수 있다.

## 5. 관측과 정량 평가

관절 변화는 **Gazebo joint2 실제 상태 → ROS /joint_states → RSP /tf → RViz** 순서로 확인한다.

```bash
ros2 run tf2_ros tf2_echo base_link link2
ros2 topic hz /joint_states
```

- `/joint_states`에서 `name` 배열의 `joint2` 인덱스와 해당 `position`을 함께 확인.
- 명령값과 측정 관절각이 정확히 같아질 때까지 걸리는 시간, 정착 오차, 진동 여부를 기록.
- Gazebo가 불안정하거나 관절이 과도하게 튀면 plugin의 `p_gain`·`d_gain`·출력 제한 및 물리 step을 검토하고 즉시 중단.
- RViz 움직임만 보고 물리 상태가 맞다고 단정하지 않는다.

## 6. 트러블슈팅

| 실패 | 우선 조치 |
|---|---|
| `ros2 run my_robot_tf joint_position_cli` 실패 | **해당 실행 파일 없음**. `my_robot_description joint_control_cli` 사용 |
| 명령 로그는 나오나 Gazebo 무반응 | `/joint2/cmd_pos` publisher/bridge; 실제 gz 토픽; plugin 로딩 |
| Gazebo 움직이나 RViz 무반응 | `/joint_states` 전송, `robot_state_publisher`, TF, RViz 설정 |
| 움직임이 출렁이거나 급격함 | 계단형 목표·PID 과도응답·물리 안정성 점검 |
| Gazebo base가 떨어지는데 RViz base가 고정 | 4.6절의 base pose TF 미구현 |

## 7. 완료 조건/응용

4개 시점(실행 전, 명령 +0.785, 명령 -0.785, 종료)의 **ROS 명령/관절 피드백/TF/화면**을 저장한다. 적어도 두 번 명령 변화와 그에 대응하는 실제 joint2 상태 변화가 확인되면 이 절의 기초 관절 제어 실습 성공으로 분류한다. 전체 로봇 위치 동기화·궤적의 부드러움은 별도 Acceptance다.

응용: `joint1`을 제어하려면 Ch03 모델에 이미 존재하는 `/model/my_robot/joint1/cmd_pos` plugin에 맞는 **ROS→Gazebo 브리지와 새로운 명령 발행자**를 구성하고 joint1의 측정 상태를 검증한다. 문서의 예시는 해당 구현을 완료한 것으로 간주하지 않는다.

[코드 리뷰 보고서](SECTION_4_7_REPORT_KO.md)
