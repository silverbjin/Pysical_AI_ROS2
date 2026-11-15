# G04B Cycle 05 — 실제 WORLD 그리퍼 파지 방향 보존 하강 목표 검증

- 날짜: 2026-11-15 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 물리 비교 기준: **PGS 고정 World** [CI #43721071561](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43721071561), Artifact #14163978713 / ZIP SHA256 `b8e2a0bbb99accef578047e714819ff25ad8abce261baeb9e76b824fdbdfbd44`.
- **상태: L0 검수 전 / L2 미실행 / G04B BLOCKED.**

## RED — 실제 관절3 고착과 하강 방향 설계 오류

기존 lower_into_bin target은 `q2+q3+qwrist`를 world tool tilt로 잘못 가정한다. 실제 원본 5DOF URDF 회전은 `Rz(q1) Ry(q2+q3) Rz(q4) Ry(qw)`로, q4≈π/2에서는 더 이상 wrist 각도 단순 합으로 world 방향을 보존하지 않는다. 기존 PGS 원본에서 high→lower 목표의 그리퍼 jaw normal 변화는 약 22.1°, tool Z축 약 25.9°. 실제 lower joint3 direct FJT residual 약 0.126236rad. **해당 자세 변화가 원인이라는 인과관계는 아직 미확정.**

## 가설과 단 하나의 새로운 변경

하강 중 잘못된 wrist 보정으로 그립이 물리적으로 비틀리면서 joint3의 하강이 막힐 수 있다. 이전 PGS fixture, original anchored robot, DART6.13 test-only lower margin, 50g rod, native contacts, 목표 XYZ, q1/q2/q3, MoveIt/FJT tolerances, 기존 동적 원통 접촉·상승·홀드·배치 ROI를 **변경하지 않는다**. 이미 관찰된 PGS world를 기준으로 **하강 q4·wrist 각도의 결정적 목표 계산**만 바꾼다.

원본 world jaw vector를 lower 목표의 `Rz(-q1)Ry(-(q2+q3))`로 역회전하고, `Rz(q4)Ry(qw)e_x`의 역을 `q4=atan2(localY,localX)`, `qw=atan2(-localZ,hypot(localX,localY))`로 풀어 변경한다. 실제 high arm JointState와 물체–손가락 FK 오프셋을 사용한다. 관절 한계 및 목표 원통 XY 6cm·높이 1.78~1.92m, tool axis 변화 ≤0.38rad 검증. 가짜 물체 위치·관절 위치 주입 금지.

기존 PGS 원본의 명목상 high 값에서 계산한 예시는 lower q4≈1.2475rad, qw≈-0.1042rad; jaw 방향 변화 이론상 0°, tool Z 방향 변화 약 17°로 감소, 예상 rod XY 약 2.4cm, 중심 높이 약 1.806m. 이는 **물리 인수 결과가 아니라 오프라인 FK 예측**이다.

## 코드·테스트

- `ci/ch07_181_jaw_axis_carry.py`: 원본 URDF 회전의 정확한 jaw 방향 보존 계산 추가.
- `ci/tests/test_ch07_181_jaw_axis_carry.py`: 기존 성공/안전 테스트에 원본 PGS 측정 관절각 기반 positive/negative TDD 추가.
- `ci/ch07_77_g04b_actual_physics_witness.py`: 환경변수 `G04B_CYCLE05_PGS_JAW_GOAL=YES`에서만 새로운 lower target 계산; 기본 경로 유지.
- `ci/ch07_77_g04b_physical_once.sh`: 같은 환경변수에서만 이미 검증된 PGS single-factor world comparator 재사용.
- `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: 물리 Job에만 해당 flag 지정, PR push의 L0는 실제 Gazebo 미실행.

## 반증/중단 기준

L0 통과 후 고정 source SHA 승인형 실제 Gazebo 단 1회. 실제 원통 양측 접촉, ≥5cm lift, 1.3s hold, high custody, lower actual q3 ≤0.01rad, 실제 wrist/world jaw, 실제 해제 및 settled bin ROI를 원래 물리 판정기로 검증한다. high가 실패하면 lower UNKNOWN. lower가 실패하면 정확한 방향 후보는 원인 해결 증거가 아님. 실패 후보는 원복하고 raw 증거를 보존한다.

## 실행 결과(추가 기록 예정)

- 개발 SHA: PENDING
- L0: PENDING / L2: NOT_RUN
- raw Artifact / ZIP SHA256: NOT_RUN
- 첫 실패·물리 판정: PENDING

**G00–G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
