# 4.7절 코드 리뷰: 로봇 조인트 위치 제어

- 기준: `main@7b7c10f`, 2026-10-20 KST
- 브랜치: `feat/ch04-section-4-7`
- 소스 점검: Ch04 패키지 및 Ch03 `my_robot_description/joint_control_cli.py`, `urdf/two_dof_arm.urdf.xacro`, `launch/sim_sync.launch.py`, `config/ros_gz_bridge.yaml`
- 결론: **BLOCKED AS WRITTEN** — 원고가 요구하는 Ch04 `joint_position_cli`는 없음. 다만 Ch03의 **joint2** 제어 노드와 브리지를 이용한 대체 실습 경로 존재.
- 실행 증거: 실제 Gazebo/ROS 시스템 시험 **NOT RUN**, GitHub 원격 정적 검토만 수행.

## 1. 코드 구현 상태

| 항목 | 원고 4.7 | 실제 `main` |
|---|---|---|
| 패키지 | Ch04 `my_robot_tf` | 제어 노드는 **Ch03 `my_robot_description`** |
| 실행 파일 | `joint_position_cli` | `joint_control_cli` (`setup.py` 등록) |
| 대상 관절 | `joint1` | `joint2` |
| ROS 제어 토픽 | `/joint1/cmd_pos` | `/joint2/cmd_pos` |
| Gazebo plugin | `JointPositionController` | `two_dof_arm.urdf.xacro`에 joint1·joint2 각각 설치 |
| Gazebo 수신 토픽 | `/model/my_robot/joint/joint1/cmd_pos`(원고) | `/model/my_robot/joint2/cmd_pos`(실제 plugin) |
| 브리지 | 원고 예제 | Ch03 sim_sync에 `...joint2/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double` 설정 |

## 2. 결함과 중요한 보완

| ID | 심각도 | 근거 | 개선 |
|---|---|---|---|
| 4.7-R1 | **High** | Ch04 `my_robot_tf/joint_position_cli.py` 부재 + entry point 없음 | 원고 실행 명령으로는 `No executable found`. Ch03 기존 `joint_control_cli`를 사용하거나 Ch04로 소스/엔트리포인트/의존성을 이관하는 변경 필요. |
| 4.7-R2 | **High** | `joint1`(원고) vs `joint2`(실제 제어 경로) | 가이드는 실제 `joint2`를 제어. 모델의 관절 축과 명령 제한 확인. |
| 4.7-R3 | **High** | 원고의 브리지 remap 방향과 실제 Gazebo plugin 토픽명이 서로 다름 | `ros2 topic list`, `gz topic -l`을 보고 **같은** ROS/Gazebo 라우팅으로 맞춘다. Ch03 sim_sync는 명시적 topic+remap으로 joint2 제어를 연결함. |
| 4.7-R4 | Medium | JointPositionController의 PID 이득이 큼(`joint2 p=500,d=5`) | 목표 각도 급변에 진동·힘 제한·물리 불안정 가능. 시뮬레이션 시 엔진 로그, 실제 관절 오차와 과도응답을 관찰. 무조건 성공으로 해석 금지. |
| 4.7-R5 | Medium | 2초마다 `-0.785 ↔ +0.785` 계단형 목표 | 부드러운 trajectory가 아님. 출력 자세 변화가 목표값과 즉시 같아지지 않는다. 속도/가속도 제한 계획 후 후속 장으로 확장. |
| 4.7-R6 | Medium | `joint_state_publisher_gui`가 실제 값의 대체품일 수 있음 | Gazebo 물리 기반 실험에서는 GUI 미실행, /joint_states는 Gazebo bridge 1곳에서만 제공. |
| 4.7-R7 | Medium | 조인트 제어 ≠ base pose 추적 | RViz에 관절 변화가 표시될 수 있어도 전체 로봇 base pose 동기화는 4.6의 미완성 과제. |

Gazebo 공식 문서상 JointPositionController의 기본 토픽은 모델/관절/축 index를 포함할 수 있고 `<topic>`으로 덮어쓸 수 있으므로, 원고의 기본 토픽 형식을 표준으로 단정하면 안 된다. **현재 모델에 명시된 실제 `<topic>`이 우선**이다.

## 3. 합격 판정 조건

1. `ros2 pkg executables my_robot_description`에서 `joint_control_cli` 확인.
2. ROS `/joint2/cmd_pos`에 2초마다 ±0.785rad 명령 전송.
3. Gazebo plugin `/model/my_robot/joint2/cmd_pos` 수신.
4. Gazebo 실제 joint2 각도가 **명령 변화에 대응**하여 움직이고, `/joint_states`·`/tf`·RViz 링크 변화가 이어짐.
5. 오버슈트, 진동, 시뮬레이션 안정성과 시간 동기화가 적정한지 별도 평가.

## 4. 검증·변경 상태

- 원격 source 구조·의존성 및 토픽 불일치: **정적 확인**.
- ROS 실행, Gazebo joint actuation, 물리 안정성, RViz: **NOT RUN**.
- 소스 변경: 없음. 검증 PASS 수치 작성하지 않음.

재현 절차는 [LAB_4_7_GUIDE_KO.md](LAB_4_7_GUIDE_KO.md)에 있다. 참고: [Gazebo JointPositionController](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1JointPositionController.html) · [Harmonic ROS 연결](https://gazebosim.org/docs/harmonic/ros2_integration/).
