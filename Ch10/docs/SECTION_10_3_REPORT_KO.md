> **사후 보완 (2026-10-21):** 이 문서는 최초 코드 리뷰 시점의 판단을 보존합니다. 이후 소스 수정과 정적 점검은 [SECTION_10_3_FIX_TEST_REPORT_KO.md](SECTION_10_3_FIX_TEST_REPORT_KO.md)를 참조하세요. 기존의 '코드 변경 없음' 기록은 최초 리뷰 당시 상태입니다.

# 10.3절 코드 리뷰 보고서 — 발끝 궤적과 착지점 생성

- 검토일: 2026-10-21 (KST)
- 원고: 첨부된 『Physical AI 실무 가이드』 10장 10.3절
- 원격 기준: `silverbjin/Pysical_AI_ROS2` main, 작업 시작 시점 `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 검토 대상: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trajectory_generator.py`, `Ch10/ros2_ws/test_trajectory.py`, `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/quadruped_controller.py`
- 판정: **코드 정적 검토 완료 / 환경 실행 및 Gazebo 물리 검증 미수행 / 종합 승인 보류**

## 핵심 결론

스탠스 상대운동과 스윙의 시작·정점·끝을 x-z 그래프로 비교하며 접지 연속성을 실험한다. 수평 보간은 `s - sin(2πs)/(2π)`, 수직 오프셋은 현행 코드의 두 구간식이다.

## 소스 기준 결함·위험 목록

| 심각도 | 발견 | 소스 근거 및 영향 | 수정 권고 |
|---|---|---|---|
| HIGH | 궤적 통합 API가 gait 설정을 무시 | `TrajectoryGenerator.generate()`의 `T_cycle=0.5`, `duty_factor=0.5`는 고정값이어서 crawl/pace 등 보행 변경 시 실제 stance 시간과 어긋난다. | 현행 planner의 frequency와 duty를 명시적으로 주입해 동일한 시간 기준을 사용. |
| HIGH | yaw를 선속도 벡터의 Z성분처럼 전달 | `quadruped_controller.py`는 `[vx,vy,wz]`를 `generate()`에 주입하고, 내부 스탠스·착지점 계산은 3D 속도 벡터처럼 다룬다. yaw 반영에 필요한 `(-ω*y,ω*x)` 계산이 없다. | 회전 명령은 leg별 원운동 접선 속도로 변환하고 z 속도는 0으로 유지. |
| MEDIUM | 좌표계 설명과 명목 위치 차이 | `TrajectoryGenerator.nominal_positions`은 [±0.12,±0.05,-0.3]으로 body-frame처럼 정의하나 10.3 원고는 hip-frame을 사용한다. | body→hip 변환 계약과 힙 오프셋의 단일 출처 명시. |
| MEDIUM | 배열 입력의 불변성·속도 평활 확인 필요 | `generate_stance`는 입력 `nominal_pos`가 list면 산술이 불가능하며, 수직 프로파일은 예제 원고의 sine과 현행 piecewise cycloid가 다르다. | np.ndarray 유효성, 양 끝 위치/수평·수직 속도, 최고점, 입력변형 여부를 수치 검증. |

## 검토 절차와 검증 수준

1. 도서 원고의 10.3절 학습 목표와 실제 저장소의 파일명·API·메시지 계약을 대조했다.
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
# 절별 검증은 짝 문서 LAB_10_3_GUIDE_KO.md 참조
```

## 수락 조건과 보류 항목

1. [ ] 시작·끝 위치는 지정된 좌표와 맞고 최고점은 기준 z + step_height이다.
2. [ ] 같은 인수로 실행할 때 출력이 재현된다.
3. [ ] 그래프는 궤적만 검증하고 Gazebo 접촉·전진 성공의 증거가 아님을 구분한다.
4. [ ] `ros2 pkg prefix my_quadruped_bot`가 현재 Ch10 workspace 설치 디렉터리를 가리키는지 확인
5. [ ] 필요한 경우 단위테스트/ros2 topic/시뮬레이터 로그와 결과 수치·실행 시간·Git SHA 보존

**결론:** 현행 소스를 변경하지 않았으며, 학습 실행의 성공을 입증하지 않았다. 근본 원인 해소 후 정적·단위·통합·Gazebo 검증을 거쳐 최종 승인해야 한다. 이 문서는 [실습 가이드](LAB_10_3_GUIDE_KO.md)와 한 쌍이다.
