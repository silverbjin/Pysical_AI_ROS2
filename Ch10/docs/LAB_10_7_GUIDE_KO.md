# 10.7절 실습 가이드 — ROS 2 통합 제어 노드

> 구분: Ch12 문서와 같은 절별 단계식 운영. 이 가이드는 **재현 절차와 합격 기준**이지, 이미 Gazebo 실습을 통과했다는 증명서는 아니다.

## 1. 학습 성과

50Hz 노드의 LPF·동적 파라미터·TF/odometry를 공부하는 절이다. 원고의 `/joint_commands`↔Gazebo 토픽 계약은 현재 YAML과 다르며, 현행 `quadruped_controller_ros2`는 실보행 통합 완료 코드가 아니다.

## 2. 사전 구성 및 안전 게이트

리포지토리의 `Ch10/ros2_ws`만 별도로 사용하며, 다른 장의 `install/setup.bash` 잔존 source가 있으면 깨끗한 새 셸에서 진행한다.

```bash
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
ros2 pkg executables my_quadruped_bot
```

사전 요구: Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic, `ros_gz_sim`·`ros_gz_bridge`·`robot_state_publisher`·`xacro`, Python NumPy 및 실습에 필요한 메시지 패키지. `colcon build`와 패키지 해석이 실패하면 **이후 제어 명령을 실행하지 않는다**. Xacro 치수, IK 모델 및 joint limit의 충돌은 [리뷰 보고서](SECTION_10_7_REPORT_KO.md)에서 먼저 확인한다.

## 3. 실제 명령 (한 줄씩 실행)

```bash
# Gazebo 터미널
ros2 launch my_quadruped_bot simulation.launch.py
# 새 터미널, 충돌하는 제어기 없이 통신 구조만 확인
ros2 run my_quadruped_bot quadruped_controller_ros2
ros2 node info /quadruped_controller
ros2 topic info /joint_states --verbose
ros2 topic echo /odom --once
ros2 param set /quadruped_controller alpha 0.2
ros2 param set /quadruped_controller gait_type pace
```

**주의:** 터미널마다 Jazzy 및 해당 Ch10 설치 환경을 source해야 한다. 예제에서 설명하는 노드의 publisher가 실제 존재하는지 `ros2 node info`, `ros2 topic info -v`로 검증한다. `ros2 topic pub -1` 단발 명령은 메시지 도착 후 velocity 상태가 갱신되는지 확인할 때만 사용하며 정지 watchdog이 없으면 실제 하드웨어에는 사용하지 않는다.

## 4. 측정·판정 체크리스트

1. [ ] **1단계:** ROS 2 50 Hz 타이머와 수신·송신 토픽을 확인한다.
2. [ ] **2단계:** `/joint_states`의 발행자 수 및 실제 물리 상태와 목표 각의 구분을 기록한다.
3. [ ] **3단계:** 파라미터 성공 응답만이 아니라 planner/frequency와 발 궤적에 실제 반영됐는지 확인한다.
4. [ ] **4단계:** odom/TF가 측정치가 아닌 적분 예측임을 실측 pose와 비교해 설명한다.

관측 결과에 `PASS / FAIL / NOT RUN` 상태를 구분해 남긴다. FAIL이라면 재현 명령, 예상값·실제값·로그, 변경한 파라미터의 전후를 기술한다. 10.8 이전에 IK-URDF 좌표계 불일치가 해결되지 않은 경우 속도나 힘을 임의로 증대하지 않는다.

## 5. 장애 처리 및 응용 실습

1. **통합 노드가 실제 보행 명령을 생성하지 않음** — 실제 GaitPlanner/TrajectoryGenerator/IK를 호출해 조인트별 목표를 계산하도록 구현.
2. **관측 토픽을 명령 토픽으로 오용** — 명령을 ROS_TO_GZ로 매핑된 12개 Float64 위치 제어 토픽으로 분리; `/joint_states`는 측정 전용.
3. **파라미터 검증과 적용이 분리** — 전 항목 검증 성공 후 원자적으로 적용하고 gait planner 상태를 재검증.
4. **추측 항법을 센서 측정 오도메트리처럼 해석할 위험** — `odom`을 command-integrated dead reckoning으로 표시하고 실제 Gazebo world pose 대비 오차 측정; 동일 odom→base_link TF를 둘 이상 발행하지 않는다.
5. **입력 명령 만료와 제어권 보호 부재** — watchdog, 속도 제한, 단독 publisher, clock/use_sim_time 및 리소스 검사.

## 6. 제출 Evidence

- [ ] `git rev-parse HEAD`, `ros2 doctor --report`, `gz sim --version` 등 환경 정보
- [ ] `ros2 node list`·`ros2 topic list -t`·필요한 `ros2 topic info -v`
- [ ] 시나리오별 시작 시각/실행 시간/명령/입력 값/관측 그래프 또는 로그
- [ ] 외란·회전 등의 주장에는 ground truth body pose·자세·관절상태 동반
- [ ] 실패 사례와 미실행 항목은 삭제하지 말고 분리 표기
- [ ] 현행 코드만으로 안정적 보행이 입증되지 않았다는 한계 서술

연결 문서: [SECTION_10_7_REPORT_KO.md](SECTION_10_7_REPORT_KO.md)
