# SECTION 3.8 — Gazebo 관절 상태·위치 제어 플러그인 리뷰

- 원고: 3.8.1~3.8.5 (JointStatePublisher, JointPositionController, bridge, 제어 테스트)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20 KST
- 대상: `urdf/two_dof_arm.urdf.xacro`의 `<gazebo>` 블록
- 판정: **설정 정적 개선 완료 / 실제 플러그인 로딩·PID 안정성 미검증**

## 발견
| ID | 심각도 | 근거·원인 | 조치 |
|---|---|---|---|
| 3.8-01 | Medium | `JointStatePublisher` 주파수가 1000Hz: 책의 GUI/ROS 토픽 실습에는 과도한 이벤트 부하 | 50Hz로 낮추고 physics `max_step_size=1ms`와 **서로 다른 주기**임을 명시 |
| 3.8-02 | Medium | joint1 PID `p=1000, i=0.1, d=10`, joint2 `p=500,i=0.1,d=5`는 실험적으로 검증된 튜닝값 아님 | 수치 변경 없이 검증 대기. 발산 시 P/D·출력제한의 단계적 실험 안내 |
| 3.8-03 | Medium | 플러그인 explicit topic은 `/model/my_robot/joint1/cmd_pos`, `/model/my_robot/joint2/cmd_pos`; ROS 측은 `/joint1/cmd_pos`, `/joint2/cmd_pos` | 3.6 YAML의 `gz_topic_name`/ `ros_topic_name`으로 매핑해야 함 |
| 3.8-04 | High (시나리오) | URDF 베이스가 물리 월드에 **고정**됐다는 증거가 없어 원고의 '항상 꼿꼿이 유지'는 보장 안 됨 | 베이스 이동/낙하와 joint 상대각 유지 판정 분리 |
| 3.8-05 | Info | `JointStatePublisher`는 Gazebo 플러그인, `joint_state_publisher_gui`는 ROS 측 가상 GUI로 전혀 다른 데이터원 | 통합 실행에서는 GUI 가상 publisher를 병행하지 말 것 |

## 코드와 공식 인터페이스 대조
Harmonic JointPositionController는 `joint_name`, `topic`, `p_gain`, `i_gain`, `d_gain`, `i_min/max`, `cmd_min/max`, `initial_position`을 지원한다. 기본 명령 토픽을 가정하지 말고 **명시된 `topic` 경로**를 확인한다. 공식 API https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1JointPositionController.html (버전별 문서와 설치 버전을 대조).

## 검증
- PASS(정적): Xacro에서 JointStatePublisher ×1, JointPositionController ×2, `joint_name` 각각 joint1/joint2, topic 설정과 브리지 명칭 대응, 상태 주기 50Hz 변경.
- NOT RUN: Gazebo `gz sim`, 플러그인 로딩, 50Hz 실측, `/joint_states` 실측, PID 수렴/진동/토크 측정.
- 선행: 3.3의 관성 중심 및 inertia 축 패치, 3.6의 브리지 패치를 병합한 통합 환경 필요.

## 실제 재현
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description spawn_robot.launch.py
# 다른 터미널:
ros2 topic pub --once /joint1/cmd_pos std_msgs/msg/Float64 '{data: 0.5}'
ros2 topic pub --once /joint2/cmd_pos std_msgs/msg/Float64 '{data: 0.5}'
ros2 topic echo /joint_states
```
토픽 발행만으로 PASS 처리 금지. 실제 joint1/joint2의 position이 유한하며 목표 근처로 이동하는지, overshoot/settling time, RTF, 베이스 움직임을 수집한다. Acceptance=`PENDING_RUNTIME_VERIFICATION`.
