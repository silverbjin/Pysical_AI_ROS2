> **사후 보완 (2026-10-21):** 이 문서는 최초 코드 리뷰 시점의 판단을 보존합니다. 이후 소스 수정과 정적 점검은 [SECTION_10_2_FIX_TEST_REPORT_KO.md](SECTION_10_2_FIX_TEST_REPORT_KO.md)를 참조하세요. 기존의 '코드 변경 없음' 기록은 최초 리뷰 당시 상태입니다.

# 10.2절 코드 리뷰 보고서 — 보행 계획기: 위상과 듀티 팩터

- 검토일: 2026-10-21 (KST)
- 원고: 첨부된 『Physical AI 실무 가이드』 10장 10.2절
- 원격 기준: `silverbjin/Pysical_AI_ROS2` main, 작업 시작 시점 `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 검토 대상: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/gait_planner.py`, `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/generalized_gait_planner.py`, `Ch10/ros2_ws/test_gait_fsm.py`
- 판정: **코드 정적 검토 완료 / 환경 실행 및 Gazebo 물리 검증 미수행 / 종합 승인 보류**

## 핵심 결론

FL/RR 대각선 위상과 FR/RL 위상 차 0.5, trot duty=0.5의 뜻과 `walk`·`pace` 오프셋을 관찰한다. 10.2절 단계에서는 물리 접촉 성공을 보장하지 않는다.

## 소스 기준 결함·위험 목록

| 심각도 | 발견 | 소스 근거 및 영향 | 수정 권고 |
|---|---|---|---|
| HIGH | 실행 진입점 오류 | `setup.py`가 `gait_planner = my_quadruped_bot.gait_planner:main`을 등록하지만, 해당 모듈에는 `main()`이 없다. | `ros2 run my_quadruped_bot gait_planner`를 실행 예제로 제시하지 말고 Python 모듈로 임포트한다. 필요하면 별도 CLI 구현. |
| MEDIUM | 시간 래핑은 단일 주기만 감산 | `GaitPlanner.update()`와 `GeneralizedGaitPlanner.update()`는 dt가 주기를 여러 번 넘는 경우 `while` 또는 `%` 처리를 하지 않아 위상/전이 타이밍이 어긋날 수 있다. | 주기 경계, 큰 dt, 0/음수 dt, 초과 범위 입력을 테스트한다. |
| MEDIUM | 상태 반환 계약 혼동 | `GaitPlanner.get_leg_states()`는 `(정규화된 phase, is_swing)` 딕셔너리를 반환한다. 원고 초기 예제의 `(contacts, phases)` 튜플과 호환되지 않는다. | `is_swing=False`를 stance로 해석하고 호출부를 현행 API로 맞춘다. |
| MEDIUM | FSM 테스트는 검증력이 부족 | `test_gait_fsm.py`는 실행한 뒤 의존성을 Mock으로 바꾸려 하며, `4.0 > sim_time >= 4.2`는 불가능한 조건이다. assert 없이 출력 위주다. | 테스트를 불변식 기반 assert로 교체하고 미끄럼/전이 시점 회귀 검사. |

## 검토 절차와 검증 수준

1. 도서 원고의 10.2절 학습 목표와 실제 저장소의 파일명·API·메시지 계약을 대조했다.
2. Python 클래스 구현, 설정, 관련 테스트 스크립트의 호출 관계를 **소스 열람 기반**으로 점검했다.
3. 본 작업 환경에는 ROS 2 Jazzy/Gazebo Harmonic 구동 권한과 원격 사용자의 WSL2 실행 증거가 없어 **실제 colcon 빌드·ROS 토픽 송수신·Gazebo 물리 실행은 수행했다고 주장하지 않는다**.
4. 따라서 오류 수준은 코드만으로 확인되는 구조적 결함 또는 실행 시 검증해야 하는 위험을 구분한다. 위 검토는 실제 시뮬레이션에서 재현된 장애 기록이 아니다.

## 재현·회귀 검증 권장 명령

```bash
# 저장소 루트에서 작업 시작
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot
colcon build --symlink-install
source install/setup.bash
# 절별 검증은 짝 문서 LAB_10_2_GUIDE_KO.md 참조
```

## 수락 조건과 보류 항목

1. [ ] 같은 시각에 FL과 RR의 위상·상태가 일치한다.
2. [ ] FR과 RL의 위상·상태가 일치하고 반대 대각선 그룹과 0.5 주기 차이가 난다.
3. [ ] 스윙/스탠스 경계에서 phase가 0부터 다시 시작함을 설명한다.
4. [ ] `ros2 pkg prefix my_quadruped_bot`가 현재 Ch10 workspace 설치 디렉터리를 가리키는지 확인
5. [ ] 필요한 경우 단위테스트/ros2 topic/시뮬레이터 로그와 결과 수치·실행 시간·Git SHA 보존

**결론:** 현행 소스를 변경하지 않았으며, 학습 실행의 성공을 입증하지 않았다. 근본 원인 해소 후 정적·단위·통합·Gazebo 검증을 거쳐 최종 승인해야 한다. 이 문서는 [실습 가이드](LAB_10_2_GUIDE_KO.md)와 한 쌍이다.
