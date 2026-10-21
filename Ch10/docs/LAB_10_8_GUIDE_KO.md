# 10.8절 실습 가이드 — Gazebo 보행·안정성 통합 검증

> 구분: Ch12 문서와 같은 절별 단계식 운영. 이 가이드는 **재현 절차와 합격 기준**이지, 이미 Gazebo 실습을 통과했다는 증명서는 아니다.

## 1. 학습 성과

원고 10.8의 네 가지 단계(기립, 제자리 스텝, 속도/회전, 10N·50N 외란)를 '실패를 분석하는 실험'으로 운영한다. 안정적 보행 성공을 가정하지 말고 실제 pose·각도·토픽·명령자 수로 판정해야 한다.

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

사전 요구: Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic, `ros_gz_sim`·`ros_gz_bridge`·`robot_state_publisher`·`xacro`, Python NumPy 및 실습에 필요한 메시지 패키지. `colcon build`와 패키지 해석이 실패하면 **이후 제어 명령을 실행하지 않는다**. Xacro 치수, IK 모델 및 joint limit의 충돌은 [리뷰 보고서](SECTION_10_8_REPORT_KO.md)에서 먼저 확인한다.

## 3. 실제 명령 (한 줄씩 실행)

```bash
# 터미널 A, Ch10 설치를 source한 뒤
ros2 launch my_quadruped_bot simulation.launch.py
# 터미널 B: 기립만 확인할 때; 다른 제어기는 끈다
ros2 run my_quadruped_bot stand_up
# 터미널 C: 독립 토픽/브리지 확인
ros2 topic list -t
ros2 topic info -v /model/my_quadruped/joint/fr_thigh_joint/cmd_pos
ros2 topic echo /clock --once
gz topic -l | grep my_quadruped
# STAND 종료 후 별도 시나리오에만 다음을 실행:
# ros2 run my_quadruped_bot trot_gait_preview
# ros2 run my_quadruped_bot trot_controllerFSM
```

**주의:** 터미널마다 Jazzy 및 해당 Ch10 설치 환경을 source해야 한다. 예제에서 설명하는 노드의 publisher가 실제 존재하는지 `ros2 node info`, `ros2 topic info -v`로 검증한다. `ros2 topic pub -1` 단발 명령은 메시지 도착 후 velocity 상태가 갱신되는지 확인할 때만 사용하며 정지 watchdog이 없으면 실제 하드웨어에는 사용하지 않는다.

## 4. 측정·판정 체크리스트

1. [ ] **1단계:** 기립 10초 동안 roll·pitch·높이·관절명령 및 낙상 여부를 기록한다.
2. [ ] **2단계:** 제자리 스텝은 실제 발 높이·접지 이벤트·대각선 동기화로 평가한다.
3. [ ] **3단계:** 저속 전진/회전은 commanded vs ground-truth displacement/yaw 및 미끄럼을 비교한다.
4. [ ] **4단계:** 외란은 적용 힘(N), 방향, 지속시간, 모델 위치, 복귀 시간, 낙상 여부를 증거로 남긴다.

관측 결과에 `PASS / FAIL / NOT RUN` 상태를 구분해 남긴다. FAIL이라면 재현 명령, 예상값·실제값·로그, 변경한 파라미터의 전후를 기술한다. 10.8 이전에 IK-URDF 좌표계 불일치가 해결되지 않은 경우 속도나 힘을 임의로 증대하지 않는다.

## 5. 장애 처리 및 응용 실습

1. **원고 예시 bridge 메시지 계약과 저장소가 다름** — 문서 실행은 저장소 YAML의 실제 12개 위치 제어 경로를 기준으로 한다.
2. **기립·보행 성능 합격 증거 없음** — 4개 시나리오의 사전/사후 상태·샘플 수·수치·로그·스크린샷·환경 버전을 확보.
3. **동일 로봇 명령 토픽의 다중 발행과 TF 충돌 위험** — 단일 컨트롤러·단일 TF 권한으로 시나리오를 수행.
4. **모델 제원·PID·접지 조건 검증 전 외란 실험 위험** — 최소 속도·기립부터 시작하고 10/50N은 GUI 환경에서 실제 재현 가능한 힘 단위/적용 지속 시간 확인 후 순차 적용.
5. **시뮬레이션 시간 구성 차이** — `/clock`, use_sim_time 및 header timestamps 일관성 확인.

## 6. 제출 Evidence

- [ ] `git rev-parse HEAD`, `ros2 doctor --report`, `gz sim --version` 등 환경 정보
- [ ] `ros2 node list`·`ros2 topic list -t`·필요한 `ros2 topic info -v`
- [ ] 시나리오별 시작 시각/실행 시간/명령/입력 값/관측 그래프 또는 로그
- [ ] 외란·회전 등의 주장에는 ground truth body pose·자세·관절상태 동반
- [ ] 실패 사례와 미실행 항목은 삭제하지 말고 분리 표기
- [ ] 현행 코드만으로 안정적 보행이 입증되지 않았다는 한계 서술

연결 문서: [SECTION_10_8_REPORT_KO.md](SECTION_10_8_REPORT_KO.md)
