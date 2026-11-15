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

- 개발 SHA: `5873726931fb66bc0ca6c1cd7a9649c763281d02`
- L0: PASS / L2: FAIL
- 원본 Artifact 14183066802 / ZIP SHA256 `3b7b1aa84ec750e029b89a1f2e7c2b130cef8d04b2b58477028bcc34643e2ade`
- 첫 실패: `lower_into_bin` joint3 물리 정체, 엄격 FJT ABORTED −5

**G00–G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## Cycle 05 실험 완료 — 실제 Gazebo 검증, 단일 가설 기각

| 항목 | 원본 증거 |
|---|---|
| 개발 SHA | `5873726931fb66bc0ca6c1cd7a9649c763281d02` |
| CI 임시 병합 checkout SHA | `a0567c7ef536042c627941381e9041affa346ca6` (PR HEAD와 git tree `83ae4b0e411904e197f281ba07c506af60daad06` 동일) |
| L0 | [#43727342663](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43727342663) **SUCCESS**, Gazebo SKIPPED |
| L2 실제 Gazebo | [#43767407800](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43767407800) **FAIL** |
| 원본 Artifact | **14183066802** |
| 다운로드한 ZIP SHA256 | `3b7b1aa84ec750e029b89a1f2e7c2b130cef8d04b2b58477028bcc34643e2ade` |
| 실물 상응 물리 접촉·상승·유지 | native 50g 원통 물체 **0.13289m 실제 상승**, 1.3초 hold drift **0.00075936m** |
| high 목표 도달 | 5관절 최대 실제 오차 **0.00864539rad**로 0.01rad 이하, custody drift 0.0030065m, bin XY 0.0132468m |
| 원본 5DOF WORLD jaw 보정 | 계산 predicted jaw change **1.49e−8rad**, 구형 오차 **0.411701rad**, predicted tool-direction change 0.305846rad |
| 실제 `lower_into_bin` | MoveGroup status4/error1, 그러나 실제 `joint3` 목표 1.25317414rad 대비 오차 **0.12574752rad** |
| 재시도 없는 단 1회 원래 strict FJT | status6, result−5 ABORTED, `joint3 desired=1.2531741401rad, actual=1.1320985811rad`, 잔차 **0.1210755591rad** (0.01rad 기준 FAIL) |
| 원통 최종 하강 당시 위치 | `[0.490547,0.212027,1.90007]m`, bin XY 오차 **0.070545m**. 원래 최대 0.09m 이내이지만 실제 release/settled ROI 미실행 |
| 물리 구동 내부 증거 | JTC reference→hardware joint3 position command 정상 전달. native JointVelocityCmd tail median **1.210756rad/s** 대비 실제 velocity median **1.12e−11rad/s**, q3 tail span **6.82e−12rad** |
| 최종 release·안착·ROI | **NOT_RUN**; 다른 성공으로 대체하지 않음 |

### 원인 가설 판정과 변경 원복

- 기구학 오류는 존재했다: 원래 q2+q3+qwrist 합으로 WORLD jaw 방향을 보존한다고 판단한 것은 틀렸다. 이번 5DOF 정확 계산으로 이론상 jaw 방향 오차가 크게 줄었다.
- 그러나 하강 joint3의 **실제 물리적 정체는 해결되지 않았다**. 목표는 joint3 물리 상한 2.0944rad 이내인데, native motion은 약 1.132rad 부근에서 멈춘다. 이 결과만으로 DART 내부 제약의 특정 원인을 단정하면 안 된다.
- **PGS world+exact jaw 목표를 활성화하는 workflow 플래그를 원복**한다. 추후 수업에서 원인을 비교할 수 있도록 원래 순수 기구학 함수·TDD와 기존 실패 원본은 유지한다.
- **동일 물리시험 재실행 금지.** 다음 사이클은 bin collision·지지면·로봇 self-collision 등 **실제 native contact 원본 구분** 또는 물리적으로 실현 가능한 하강/해제 지점 검토에 집중한다.

### 교육용 RED→GREEN→검증→회고

1. RED: 이전 PGS 시험은 하강 q3 0.126rad 미도달 및 손목/world 축 불일치를 제시했다.
2. GREEN(수치/기구학): 정확한 URDF 회전 순서를 적용하고 단위시험으로 world jaw 방향 보존을 확인했다.
3. 실제 물리 L2: 그리퍼 방향 개선에도 joint3는 native command와 actual velocity가 어긋났고, FJT ABORTED. **물리 기능 GREEN 아님**.
4. 회고: 수학적으로 정확한 기구학 개선이 물리 접촉 제약을 자동으로 해결하지 않는다. 실패 후 원인 후보의 활성화 플래그를 되돌리고 원본·보고서를 보존한다.

**Cycle 05 CLOSED / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
