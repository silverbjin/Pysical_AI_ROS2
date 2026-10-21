> **사후 보완 (2026-10-21):** 이 문서는 최초 코드 리뷰 시점의 판단을 보존합니다. 이후 소스 수정과 정적 점검은 [SECTION_10_4_FIX_TEST_REPORT_KO.md](SECTION_10_4_FIX_TEST_REPORT_KO.md)를 참조하세요. 기존의 '코드 변경 없음' 기록은 최초 리뷰 당시 상태입니다.

# 10.4절 코드 리뷰 보고서 — 다리 역운동학 및 FK 교차 검증

- 검토일: 2026-10-21 (KST)
- 원고: 첨부된 『Physical AI 실무 가이드』 10장 10.4절
- 원격 기준: `silverbjin/Pysical_AI_ROS2` main, 작업 시작 시점 `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 검토 대상: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/inverse_kinematics.py`, `Ch10/ros2_ws/test_ik.py`, `Ch10/ros2_ws/test_ik_interactive.py`, `Ch10/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`, `Ch10/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro`
- 판정: **코드 정적 검토 완료 / 환경 실행 및 Gazebo 물리 검증 미수행 / 종합 승인 보류**

## 핵심 결론

원고에서 요구한 FK(IK(P))의 1mm 기준은 '동일한 수학 모델 내부' 검증일 뿐, Gazebo URDF 관절 축 일치성을 자동 증명하지 않는다. IK 단독 수학 검증과 시뮬레이션 물리 검증을 두 단계로 나눈다.

## 소스 기준 결함·위험 목록

| 심각도 | 발견 | 소스 근거 및 영향 | 수정 권고 |
|---|---|---|---|
| CRITICAL | IK와 실제 URDF의 길이·회전 영점이 불일치 | `InverseKinematics`: l1=0.05m, l2=l3=0.20m. Xacro: hip_length=0.08m, thigh_length=0.25m, calf_length=0.25m, thigh joint rpy=0 1.2 0, calf joint rpy=0 -2.4 0. 단순 2-link FK와 Gazebo 모델이 다르다. | xacro 확장→URDF joint origin/axis 추출→독립 FK로 맞춘 뒤 IK 분기/부호/offset 수정. |
| HIGH | 작업공간 밖 목표를 끝점으로 클램프해 성공처럼 반환 | `solve()`는 최대 리치 초과 시 x,z_prime을 재조정하고 값은 반환한다. 호출자는 원 요청 좌표에 도달했다고 오인할 수 있다. | unreachable 신호와 projected 목표/오차를 분리하고 범위 검사. |
| HIGH | 관절 한계 검사 부재 | `solve()`는 arccos 입력을 clamp하지만 실제 URDF 하한/상한, 지면 간섭, 자체 충돌 조건은 검사하지 않는다. | joint limit과 FK/URDF 교차 검증을 통과하지 않으면 Gazebo 이동 실습 차단. |
| MEDIUM | FK 테스트가 동일 가정을 공유 | `test_ik.py`의 수학적 FK는 IK와 같은 길이·영점 가정이다. 100개 무작위 좌표의 FK(IK(P)) 테스트만으로 실제 URDF 일치 검증 불가. | 난수 seed, 양측 미러링, 에러 분포, URDF 독립 FK, 임계치 초과 음성 사례를 추가. |

## 검토 절차와 검증 수준

1. 도서 원고의 10.4절 학습 목표와 실제 저장소의 파일명·API·메시지 계약을 대조했다.
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
# 절별 검증은 짝 문서 LAB_10_4_GUIDE_KO.md 참조
```

## 수락 조건과 보류 항목

1. [ ] 독립 3D FK와 IK의 발끝 위치 오차를 좌/우 다리별 검증한다.
2. [ ] 목표가 작업공간 밖이거나 조인트 리미트를 벗어나면 정상 수행으로 판정하지 않는다.
3. [ ] 기구학 수학 테스트와 URDF 일치성 검사를 각각 증거로 남긴다.
4. [ ] `ros2 pkg prefix my_quadruped_bot`가 현재 Ch10 workspace 설치 디렉터리를 가리키는지 확인
5. [ ] 필요한 경우 단위테스트/ros2 topic/시뮬레이터 로그와 결과 수치·실행 시간·Git SHA 보존

**결론:** 현행 소스를 변경하지 않았으며, 학습 실행의 성공을 입증하지 않았다. 근본 원인 해소 후 정적·단위·통합·Gazebo 검증을 거쳐 최종 승인해야 한다. 이 문서는 [실습 가이드](LAB_10_4_GUIDE_KO.md)와 한 쌍이다.
