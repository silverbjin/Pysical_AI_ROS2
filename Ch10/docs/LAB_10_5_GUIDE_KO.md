# 10.5절 실습 가이드 — 트롯 보행과 FSM 통합

> 구분: Ch12 문서와 같은 절별 단계식 운영. 이 가이드는 **재현 절차와 합격 기준**이지, 이미 Gazebo 실습을 통과했다는 증명서는 아니다.

## 1. 학습 성과

FL/RR과 FR/RL의 대각선 대칭 궤적, 기립→정지→보행→감속/복구 FSM, 선속도/요속도의 발끝 변환을 연결한다. 현행 `trot_controllerFSM` 엔트리포인트는 존재하지만 움직임 성공은 검증되지 않았다.

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

사전 요구: Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic, `ros_gz_sim`·`ros_gz_bridge`·`robot_state_publisher`·`xacro`, Python NumPy 및 실습에 필요한 메시지 패키지. `colcon build`와 패키지 해석이 실패하면 **이후 제어 명령을 실행하지 않는다**. Xacro 치수, IK 모델 및 joint limit의 충돌은 [리뷰 보고서](SECTION_10_5_REPORT_KO.md)에서 먼저 확인한다.

## 3. 실제 명령 (한 줄씩 실행)

```bash
# 터미널 A: Gazebo (Ch10/ros2_ws/install/setup.bash source 후)
ros2 launch my_quadruped_bot simulation.launch.py
# 터미널 B: 하나의 제어기만 실행 (기존 stand_up 등 종료)
ros2 run my_quadruped_bot trot_controllerFSM
# 터미널 C: 짧은 저속 명령으로 초기 점검
ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.05}}"
ros2 topic info -v /model/my_quadruped/joint/fl_thigh_joint/cmd_pos
```

**주의:** 터미널마다 Jazzy 및 해당 Ch10 설치 환경을 source해야 한다. 예제에서 설명하는 노드의 publisher가 실제 존재하는지 `ros2 node info`, `ros2 topic info -v`로 검증한다. `ros2 topic pub -1` 단발 명령은 메시지 도착 후 velocity 상태가 갱신되는지 확인할 때만 사용하며 정지 watchdog이 없으면 실제 하드웨어에는 사용하지 않는다.

## 4. 측정·판정 체크리스트

1. [ ] **1단계:** 기립 중 발 위치·관절 목표가 불연속적으로 점프하지 않는지 기록한다.
2. [ ] **2단계:** FL/RR와 FR/RL 쌍의 위상을 로그와 관절 목표로 교차 확인한다.
3. [ ] **3단계:** 짧은 이동·정지 후 네 발이 지면에 붙는지, 이동량은 실제 Gazebo 모델에서 계측한다.

관측 결과에 `PASS / FAIL / NOT RUN` 상태를 구분해 남긴다. FAIL이라면 재현 명령, 예상값·실제값·로그, 변경한 파라미터의 전후를 기술한다. 10.8 이전에 IK-URDF 좌표계 불일치가 해결되지 않은 경우 속도나 힘을 임의로 증대하지 않는다.

## 5. 장애 처리 및 응용 실습

1. **실제 URDF와 IK 제원의 불일치가 통합 보행에도 전파** — 시뮬레이터의 정확한 joint FK를 기준으로 오프셋과 leg-local 타깃을 재설계.
2. **정지 명령 이후의 안전 보장 없음** — 마지막 수신 시각·명령 만료·감속·네 다리 착지 확인을 정의.
3. **crawl에서 잘못된 stance 시간** — `T_stance=duty_factor/frequency`를 사용하고 전환 시 궤적 연속성 검증.
4. **원고 실행 패키지명과 실제 패키지명 불일치** — Ch10 빌드·source 후 실제 명령으로 교체.
5. **테스트의 독립적 물리 검증 없음** — 독립 단위테스트와 Gazebo 실제 접지·몸체 pose 증거 필요.

## 6. 제출 Evidence

- [ ] `git rev-parse HEAD`, `ros2 doctor --report`, `gz sim --version` 등 환경 정보
- [ ] `ros2 node list`·`ros2 topic list -t`·필요한 `ros2 topic info -v`
- [ ] 시나리오별 시작 시각/실행 시간/명령/입력 값/관측 그래프 또는 로그
- [ ] 외란·회전 등의 주장에는 ground truth body pose·자세·관절상태 동반
- [ ] 실패 사례와 미실행 항목은 삭제하지 말고 분리 표기
- [ ] 현행 코드만으로 안정적 보행이 입증되지 않았다는 한계 서술

연결 문서: [SECTION_10_5_REPORT_KO.md](SECTION_10_5_REPORT_KO.md)
