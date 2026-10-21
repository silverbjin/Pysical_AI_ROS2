# 10.6절 실습 가이드 — 페이싱·바운딩·크롤 및 전이

> 구분: Ch12 문서와 같은 절별 단계식 운영. 이 가이드는 **재현 절차와 합격 기준**이지, 이미 Gazebo 실습을 통과했다는 증명서는 아니다.

## 1. 학습 성과

trot/pace/bound/crawl의 위상 배열과 duty, frequency를 테이블로 관찰하고 '요청됨'과 '전환 적용됨'을 구별한다. 서비스 방식은 원고에 제안되어 있지만 현재 작동하는 서비스 서버는 확인되지 않는다.

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

사전 요구: Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic, `ros_gz_sim`·`ros_gz_bridge`·`robot_state_publisher`·`xacro`, Python NumPy 및 실습에 필요한 메시지 패키지. `colcon build`와 패키지 해석이 실패하면 **이후 제어 명령을 실행하지 않는다**. Xacro 치수, IK 모델 및 joint limit의 충돌은 [리뷰 보고서](SECTION_10_6_REPORT_KO.md)에서 먼저 확인한다.

## 3. 실제 명령 (한 줄씩 실행)

```bash
cd Ch10/ros2_ws
PYTHONPATH=src/my_quadruped_bot python3 - <<'PY'
from my_quadruped_bot.generalized_gait_planner import GAIT_LIBRARY,GeneralizedGaitPlanner
for k,g in GAIT_LIBRARY.items():
    print(k,g.duty_factor, g.offsets.tolist(),g.frequency)
p=GeneralizedGaitPlanner('trot')
p.set_gait('crawl')
for i in range(52):
    p.update(0.01)
print('after 0.52s:',p.current_gait.name,p.get_leg_states())
PY
ros2 interface show my_robot_interfaces/srv/SetGait
ros2 service list -t | grep set_gait || true
```

**주의:** 터미널마다 Jazzy 및 해당 Ch10 설치 환경을 source해야 한다. 예제에서 설명하는 노드의 publisher가 실제 존재하는지 `ros2 node info`, `ros2 topic info -v`로 검증한다. `ros2 topic pub -1` 단발 명령은 메시지 도착 후 velocity 상태가 갱신되는지 확인할 때만 사용하며 정지 watchdog이 없으면 실제 하드웨어에는 사용하지 않는다.

## 4. 측정·판정 체크리스트

1. [ ] **1단계:** 4개 gait의 위상·동시 스윙 다리 조합을 확인한다.
2. [ ] **2단계:** 전환 요청 직후와 주기 완료 이후 활성 gait가 다른지 확인한다.
3. [ ] **3단계:** `set_gait` 서비스가 없다면 호출 성공으로 기록하지 않고 미구현으로 표시한다.

관측 결과에 `PASS / FAIL / NOT RUN` 상태를 구분해 남긴다. FAIL이라면 재현 명령, 예상값·실제값·로그, 변경한 파라미터의 전후를 기술한다. 10.8 이전에 IK-URDF 좌표계 불일치가 해결되지 않은 경우 속도나 힘을 임의로 증대하지 않는다.

## 5. 장애 처리 및 응용 실습

1. **서비스 정의만으로는 서비스를 호출할 수 없음** — `ros2 service list -t`로 부재 확인 후 서비스 서버 구현/테스트.
2. **원고와 GAIT_LIBRARY의 crawl 오프셋 불일치** — 실제 다리 순서 FL/FR/RL/RR과 접지 안정성 기준으로 한 세트를 선택하여 원고와 통일.
3. **전이와 파라미터 변경의 연속성 미검증** — 전후 발끝 위치/속도·접촉 플래그를 비교하고 불연속 시 보간·중립 자세 경유.
4. **공유 객체 변형 및 큰 dt 처리** — 인스턴스별 config 복사·dt modulo/다중 주기 처리와 reset 추가.
5. **지원 gait 목록이 컨트롤러 간 불일치** — 하나의 gait registry로 UI·서비스·모듈을 일원화.

## 6. 제출 Evidence

- [ ] `git rev-parse HEAD`, `ros2 doctor --report`, `gz sim --version` 등 환경 정보
- [ ] `ros2 node list`·`ros2 topic list -t`·필요한 `ros2 topic info -v`
- [ ] 시나리오별 시작 시각/실행 시간/명령/입력 값/관측 그래프 또는 로그
- [ ] 외란·회전 등의 주장에는 ground truth body pose·자세·관절상태 동반
- [ ] 실패 사례와 미실행 항목은 삭제하지 말고 분리 표기
- [ ] 현행 코드만으로 안정적 보행이 입증되지 않았다는 한계 서술

연결 문서: [SECTION_10_6_REPORT_KO.md](SECTION_10_6_REPORT_KO.md)
