# G04B Cycle 02 — 원본 재분석, 관절 구동 측정 데이터 의미 오류 수정

- 일시: 2026-11-15
- Issue #181 / Draft PR #202, `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- Cycle 01 기준 원본: source SHA `16bb85dcf7a1be8ca17c6a4e1dc4134b108b8a5f`
- CI [#43719033640](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43719033640) **FAIL**, Artifact **#14164070632**
- ZIP SHA256 `96362eace97d021acfeb47979f35d2fefcd516054547d0b937213e97fbe211e5`
- **실제 Gazebo L2 추가 수행: 0회** (기존 원본 오프라인 재분석)
- 상태: **Cycle 02 L0 검증 예정 / G04B BLOCKED**

## RED — 진단기 자체의 최초 실패

Cycle 01 `high_joint2_causal_native_audit.json`은 hardware 위치 명령의 마지막 값이 `0`인 것처럼 기록했다. 그러나 원본 `g04b_physical_receipt.json`의 hardware에는 서로 다른 필드 `command_interface.joint2/position`과 `command_interface.joint2/position.is_limited`가 존재한다. 후자의 0은 **limit flag**이지 position command가 아니다.

이 문제를 수정하지 않으면 정상적인 목표 전달을 `0rad`의 하드웨어 명령으로 오진하고, 잘못된 Gazebo 보정을 개발할 수 있다.

## GREEN — 원본 필드와 native 응답에 일치하는 판정

- `command_interface.joint2/position` 필드 **정확한 이름 일치**로만 hardware 목표 채택. `.is_limited` 플래그 제외.
- 실제 hardware end command = **+0.10859885014736367rad**, JTC reference end와 일치.
- native high Goal `65.556–68.676`초 구간 position **−0.06686895→+0.09474rad**, 즉 장기간 초기 고착이 아니라 실제로 운동했다.
- **반증 가능한 후속 구간:** Goal 완료 후 sim `68.976–69.376` 근처 `JointVelocityCmd`가 약 **+0.124rad/s**인 반면 native 실제 velocity는 급감. `68.976–69.076` 구간 실제 position 변화 약 **0.000040rad**, `69.176–69.676` 구간 약 **0.000007rad**.
- 새 분석기는 Goal 종료 **+0.2~+0.7s** pre-physics ECS에서 8회 이상 측정하고, 비영(>0.05rad/s) 명령, 실제 거의 정지(<0.001rad/s), 실제 변위(<0.0005rad)를 모두 만족해야 `HIGH_JOINT2_POST_RESULT_NATIVE_STALL_WITH_NONZERO_CMD`을 반환한다. 자료가 없으면 UNKNOWN 또는 기존 제한 판정 유지.
- `JTC→HW` 전달 오류/전 구간 고착 가설은 **기각**. **DART 특정 접촉·제약의 근본 원인은 미확정**. `gz_ros2_control` position interface는 position error를 Gazebo joint velocity로 변환하므로, native 명령과 실제 속도를 직접 비교해야 한다. <https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html>

## 변경 결과물 및 회귀

- `ci/ch07_181_high_joint2_native_audit.py` — 정확한 hardware position field, native 종료 후 0.5s 판정
- `ci/tests/test_ch07_181_high_joint2_native_audit.py` — `.is_limited` 잘못된 0, 종료 후 고착, 실제 운동 및 누락 입력의 negative TDD
- **CI L0:** 이 커밋에서 확인. **Gazebo L2:** NOT_RUN (새 실험 가치 없음).
- 기능 코드·URDF·실제 물리 파지·MoveGroup·FJT·contact/ROI 판정 **변경 없음**.

## 다음 Cycle 03의 단일 판단

원본 Gazebo native의 **접촉쌍·DART joint 제약·몸체 상태** 중 한 가지 원인 정보를 더 확보해야 한다. 기왕의 ZIP에서 확인 가능한 native contact는 `rod↔finger1`, `rod↔finger2`뿐이며 support contact는 고위치 시간대에 미검출이다. 이는 contact friction·solver fault를 증명하지 않는다. 무작위 gain·speed·friction sweep/물리 CI 반복을 금지한다.

**교육용 교훈:** 데이터베이스·ROS introspection의 `.is_limited` 같은 메타데이터 필드를 수치 명령과 구분해야 한다. 빨리 테스트를 반복하는 것보다 첫 관측 단절의 인과 사슬을 올바로 정의하는 것이 중요하다.

**정식 인수:** G00–G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.
