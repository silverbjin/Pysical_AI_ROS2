# 6.6절 실습 가이드 — Gazebo에 MoveIt 궤적 실제 전달하기

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.6절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 목표
Planning(뇌) → FollowJointTrajectory Action(제어 계약) → gz_ros2_control(하드웨어 추상화) → Gazebo 물리 및 /joint_states 피드백을 **로그와 화면으로 연결**한다.

## 준비
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix gz_ros2_control
ros2 pkg prefix ros_gz_sim
```
WSL2/Ubuntu 24.04에서는 Gazebo Harmonic와 WSLg 렌더링 확인 필요. 다른 장 workspace의 `install/` 오버레이가 섞인 경우 **새 터미널**에서 Jazzy와 Ch06 워크스페이스만 source한다.

## 실제 런치 명령
```bash
# 터미널 A: 현재 저장소의 실제 파일명 (대소문자 그대로)
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws && source install/setup.bash
ros2 launch my_robot_moveit_config Gazebo_moveit.launch.py use_sim_time:=true
```
`demo_gazebo.launch.py`는 현재 코드베이스에 없다. 이 런치는 모델/컨트롤러 서비스 초기화 순서를 보장하지 않으므로 **spawner 상태와 오류를 먼저 확인**해야 한다.

터미널 B(별도 Jazzy + Ch06 source):
```bash
ros2 control list_controllers
ros2 action list -t
ros2 action info /arm_group_controller/follow_joint_trajectory
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
ros2 run tf2_ros tf2_echo base_link link_wrist
```
토픽/액션이 없거나 `inactive`이면 실행으로 넘어가지 않는다. 모델이 Gazebo에 존재하는지 확인하고 gz_ros2_control plugin 오류/서비스 startup race를 먼저 해결한다.

## 제어 실습(6.4 BLOCKER 해결 후)
```bash
# 터미널 C: 위 점검 후에만 실행
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws && source install/setup.bash
ros2 run my_robot_control hello_node
```
현재 `hello_node`의 URDF 경로·IK 목표·성공 로그에도 6.4의 미수정 문제가 있으므로 위 명령은 아직 정상 통합 테스트로 인증되지 않았다.

## 판정표
| 구간 | PASS의 기준 |
|---|---|
| ROS ↔ Gazebo | /clock 진행, gz entity/model 확인 |
| Controller | joint_state_broadcaster, arm_group_controller=active |
| Action | `follow_joint_trajectory` 서버 존재, goal accepted 및 result 성공 |
| Feedback | gazebo 실측 joint_states와 TF/FK 일치 |
| 안전 | 관절/속도 제한 위반 없음, 로봇 모델 비정상 물리 충돌 없음 |

## 고장 대응
- controller_manager timeout → gz_ros2_control 플러그인 로드와 spawner 시작 순서.
- Gazebo만 움직임/RViz 불일치 → TF 중복·`robot_description`·joint_states/clock 타임스탬프.
- plan 성공/실행 실패 → action 이름, 활성 controller 및 조인트 목록.
- 모델 붕괴 → 관성 원점/관절 축/접촉/중력 설정.

기록: launch 로그, `list_controllers`, /clock, /joint_states, action 결과, RViz+Gazebo 스냅샷. [보고서](SECTION_6_6_REPORT_KO.md).
