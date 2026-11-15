# G04B 개발·분석·디버깅 Cycle 01 — 고위치 joint2 실제 명령 전달 경계

- 날짜: 2026-11-15
- Issue: #181 / Draft PR #202
- 기준 main: `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 기준 HEAD: `304b68519bbeb5111b7a7a990e9f9ca367b2a57b`
- **상태: 시험 준비 / G04B BLOCKED (CI L2 결과를 보고서 후속 커밋에 기록)**
- 방법: Architecture-First → 기존 실패 원본 분석 → 하나의 반증 가능한 가설 → read-only 계측 + L0 → 승인형 L2 1회 → Artifact 감사 → 보고서 갱신

## 1. 기존 실패 원본(이전 실행, 새 수정의 PASS 증거 아님)

- [Run #43714625440](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43714625440), SHA `a7ced054e024ce4eeac24584d113346cdc34b049`; 원본 Artifact #14162335655, ZIP SHA256 `433a6b3898eabd7ff4f5debb96888d01456d2ed09e3c4218cad34815744badab`.
- 실제 5관절 high MoveGroup 후 joint2 오류 0.01253rad(기준 0.01rad). 추가 직접 FJT 시 desired 0.105683816858rad, actual 0.093309155752rad, status 6/error -5. 접촉·상승·hold는 실제 성공했지만 하강·release·ROI 미실행.
- 실패한 직접 FJT 후보는 `f4f0e55a...`에서 원복. 이 사이클은 **보정/하드웨어 동작 변경 없이** 최초 제어–물리 전달 경계를 측정한다.

## 2. 단일 가설과 반증 계획

**가설:** high MoveGroup 종료 직전 joint2 오차가 남는 이유를 `JTC reference → hardware position command → ECS JointVelocityCmd → native JointPosition` 중 한 경계에서 확인할 수 있다.

예상 반증: 명령 자체 누락이라면 JTC/HW 경계, 명령이 native에 도달했는데 변위가 없다면 DART 제약/물리 경계, 실제 joint2가 이동하지만 잔차가 남으면 track/목표 종료 조건 또는 접촉 부하를 후속 검토한다. 자료 부재는 UNKNOWN이다.

## 3. 적용 코드(수정 요인: 관측 범위만)

- `ci/ch07_77_g04b_actual_physics_witness.py`: high MoveGroup 발행·결과 구간의 controller reference/feedback/error 및 hardware command 원본 보존. 실패 예외에서도 receipt 기록.
- `ci/ch07_181_rod_trace/finger_ecs_trace.cc`: 이미 `joint2` pre/post read-only 관측 구현. command/physics 변경 없음.
- `ci/ch07_181_high_joint2_native_audit.py`: 같은 sim-time 구간의 native ECS와 컨트롤러 관측을 연결. **물리 PASS 반환 금지**.
- `ci/tests/test_ch07_181_high_joint2_native_audit.py`: 명령 누락·ECS 누락·관절 미이동을 정확하게 구분하는 L0 TDD.
- 기존 G04B 진짜 양측 접촉·lift≥0.05m·hold≥1.3s·release/settled ROI와 허용오차 모두 유지.

## 4. 실험 실행·원본 결과

- **L0:** PASS — Run #43718972198
- **L2:** FAIL — Run #43719033640 (실제 Gazebo 승인형 1회)
- **Artifact/ZIP SHA256:** #14164070632 / 96362eace97d021acfeb47979f35d2fefcd516054547d0b937213e97fbe211e5
- **실제 첫 실패 및 반증 여부:** joint2 high 실제 오차 0.0130665rad; ROS→hardware 누락은 기각, native 말기 명령–운동 불일치는 관측됨

## 5. 교육용 회고

- 물리 실패에서 Action SUCCEEDED는 실제 관절 추종 증명이 아니다.
- 목표값 재전송은 기존 실행에서 반증됐다. 새 가설에는 관측할 신호와 반증 기준을 먼저 정의한다.
- 이미 성공한 물체 상승을 별도 실험으로 재검증하지 않고 한 번의 필요한 시나리오에서 부수적으로 재사용한다.

**남은 인수:** G04B BLOCKED, G05 NOT_RUN, Ch10 HOLD, Owner WSL2 NOT_READY. 후속 실험 없이 완료 승격하지 않는다.

## 6. Cycle 01 원본 CI·실측 결과 — CLOSED / G04B BLOCKED

| 구분 | 고정 증거 |
|---|---|
| 계측 코드·시험 당시 source SHA | `16bb85dcf7a1be8ca17c6a4e1dc4134b108b8a5f` |
| 자동 L0 계약 | [#43718972198](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43718972198) **SUCCESS** |
| 단일 실제 Gazebo CI | [#43719033640](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43719033640) **FAIL** (이 실패는 안전 검사에 의해 정상적으로 거부됨) |
| 원본 GitHub Artifact | **14164070632** (`book-ch07-77-g04b-actual-contact-43719033640`) |
| 원본 ZIP SHA256 | `96362eace97d021acfeb47979f35d2fefcd516054547d0b937213e97fbe211e5` |
| 원본 실패 사유 | `G04B_181_HIGH_MOVEGROUP_ACTUAL_JOINT_TRACKING_FAILED` |
| 실제 고위치 관절 추종 오차 | **joint2 0.013066500898686592rad**, 기존 정밀 제한 **0.01rad** 초과 |
| 물리적 상승·유지 | 동적 rod 상승 **0.14046m**, 1.3s hold drift **0.001403407638571m**; 독립 G04B 전체 PASS 아님 |
| Goal/물리 작업 범위 | Arm Goal 8, Gripper Goal 3; 하강·해제·settled ROI **NOT_RUN** |

### 6.1 동일 시각의 명령·실제 응답

- 고위치 MoveGroup 관찰창: sim **65.556–68.676초**, JTC **285** 샘플, hardware data **570**개 필드 샘플, native ECS **1,380**개 pre/post 샘플.
- 실제 hardware `command_interface.joint2/position`은 최초 **−0.0668689505157rad → 최종 +0.108598850147rad**. 별도 `command_interface.joint2/position.is_limited=0` 플래그가 함께 발행됐으며 **위치 명령으로 취급하면 안 됨**. 초기 자동 감사에서 hardware final 0으로 잘못 표기된 원인이다.
- JTC `reference_joint2_rad` 최종 **+0.108598850147rad**, `feedback_joint2_rad` 최종 **+0.094788431194rad**, 오차 **+0.013810418953rad**. reference→hardware 전달 실패 가설은 이번 관찰에서 **기각**.
- Native ECS는 실제로 joint2를 이동시킴: first **−0.06686895rad → high result +0.09474rad**, `JointVelocityCmd` 최대 **0.17399197349rad/s**. 따라서 **전체 Goal 구간 동안의 완전 고착**은 아님.
- 고위치 결과 직후에는 속도 명령이 **약 +0.124rad/s로 지속**하지만 실제 속도는 0에 가까워지는 패턴. Sim **68.976–69.076초** native 위치 변화 약 **0.0000401rad** / sim **69.176–69.676초** 약 **0.00000725rad**. 이는 로봇이 목표에 정확히 도달했다는 뜻이 아니라 **nonzero velocity command와 native 실제 운동 사이의 말기 불일치**.
- 기존 native contact stream에서 sim 65초 이후 확인한 실제 충돌쌍은 **rod↔finger1**, **rod↔finger2**이고 rod↔support 접촉은 없었다. 원인 후보는 **접촉·물리 제약·속도 인터페이스**로 한정되지만, 접촉 기록만으로 DART 내부 제약 원인을 확정할 수 없다.

### 6.2 가설별 결론 및 회고

| 원인 가설 | 결론 | 근거 |
|---|---|---|
| MoveGroup이 joint2 목표를 hardware로 전달하지 않았다 | **기각** | JTC reference와 hardware command 목표 일치 |
| Gazebo가 joint2 속도 명령을 전혀 받지 않았다 | **기각** | native pre-physics `JointVelocityCmd` 실제 관측 |
| joint2가 전 구간 고착됐다 | **기각** | native JointPosition 실제 변화 약 0.162rad |
| 종료 직전 nonzero cmd에도 실제 운동이 정체됐다 | **지지되는 관측** | high 종료 이후 native velocity 거의 0 |
| DART의 특정 접촉 제약이 원인이다 | **미확정** | contact pair는 관측했지만 내부 제약 force·충돌 영향 분리 불가 |

### 6.3 다음 사이클로 넘길 유효한 작업

**Cycle 02: 원본 Artifact 재사용(새 Gazebo L2 0회)**. `.is_limited` 플래그를 실제 position command와 엄격히 분리하고, 종료 전후 마지막 0.5초의 속도 명령–실제 속도–위치 변화량을 독립 계산하는 판정기를 개발한다. 같은 샘플에서 **원인 가설 하나와 반증 조건**을 재설정할 때까지 새로운 물리 주행·gain/마찰/solver 스윕 금지.

**Cycle 01 최종 판정:** 개발·계측·L0·1회 Gazebo 실험·원본 감사 완료. **G04B BLOCKED**, G05 NOT_RUN, Ch10 HOLD. 이 보고서의 GitHub 커밋은 실험 당시 source SHA와 다르므로, 보고서 수정만으로 이전 물리 결과를 현재 HEAD의 PASS로 승격하지 않는다.
