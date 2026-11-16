# G04B Cycle 07 — 목적지 지지면의 실제 접촉 원인 계측

- 날짜: 2026-11-16 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 이전 Cycle06 실제 원본: [Run #43769574949](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43769574949), Artifact #14183955993 / ZIP SHA256 `4ee87eeccaef5f40d46b9807bfd511d1659147492b902351a976d92baab20878`
- 현재 G04B **BLOCKED**, G05 NOT_RUN, Ch10 HOLD

## 1. 첫 실패와 아직 모르는 것

동적 원통 파지·상승 0.11407m, high bin XY 오차 0.01282m, custody 유지. 목표를 물리 정체 구간 밑으로 낮춘 새 Cycle06 q3=1.05rad에서도 실제 q3가 **0.99816rad** 근처에서 정체, command≈0.525rad/s 대 actual velocity≈0.0000001rad/s. 물체 실제 중심 ≈[0.51458,0.23484,1.93606]m, 그리퍼 FK 위치와 거의 일치. 최종 release/settled ROI NOT_RUN.

이 관찰은 q3의 고정 상한에 의한 실패와 다르며, 하강 중 **다른 물체 또는 목적지 지지면 충돌**이라는 후보를 남긴다. 하지만 기존 native contact는 rod↔finger 및 원래 shelf의 contact만 기록했으므로, 목적지 support와 arm link의 실제 접촉쌍은 아직 증거가 없다.

## 2. 한 가지 반증 가능한 관측 가설

**목적지 bin collision geometry가 arm/link 또는 rod와 접촉한 시간에 q3의 native 실제 속도가 정체하는지** 실측한다.

- static bin support centre [0.55,0.25,1.63]m, collision box 0.30×0.30×0.20m, top 1.73m.
- bin_support의 **기존 bin_collision에만 read-only contact SENSOR**를 추가한다. Bin collision 크기, pose, static, gravity, friction, robot/rod/Goal은 모두 불변.
- 비교 물리 조건은 직전 Cycle06의 PGS + exact WORLD jaw + reachable lower waypoint를 동일하게 유지한다. 새 변수는 **contact sensor 하나**.
- collision records가 q3 정체와 겹치면 접촉 후보를 좁히고, bin 접촉이 없더라도 contact 시스템·시각 유효성 없는 단정은 금지. 원인 확정까지 G04B BLOCKED.

## 3. 코드와 검증 계획

- `ci/ch07_181_bin_contacts_readonly.py`: 테스트 월드 XML 구조 검증, bin contact sensor 한 개 추가, 제거 후 전체 XML 동일성 검증. Contact system/plugin 중복 불허.
- `ci/tests/test_ch07_181_bin_contacts_readonly.py`: 변경 범위 및 0.30m bin geometry·PGS physics·mass 불변·중복 센서/가짜 collision 거부.
- `ci/ch07_77_g04b_physical_once.sh`: Gazebo Goal 전 native bin topic 유효성 검증 후 원본 `diag_bin_contacts.log`로 기록. 센서가 준비되지 않으면 시험 전 STOP.
- `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: L0에서 해당 코드/TDD를 검사, 실제 L2는 opt-in `g04b-physics-once` 이벤트 1회.
- CI Artifact에 raw bin contact, 기존 joint3 JTC→HW→native ECS 및 dynamic rod 좌표·native contact 원본을 함께 보존.
- **L0:** PASS #43770546088 / **L2:** FAIL #43770622882 / Artifact: #14184565359.

## 4. 교육용 디버깅 기준

1. 관측 사실(토픽 존재·native collision pair·timestamp)과 원인 주장(DART contact constraint)을 구분한다.
2. READ-ONLY sensor를 추가하면서 충돌 형상·물리 mass·마찰을 바꾸지 않아 인과 실험을 보존한다.
3. 실제 new BIN contact가 없으면 collision 가설을 기각하기 전에 기록 시각과 sensor 활성 상태를 검증한다.
4. 실제 Gazebo가 FAIL하면 그 원본을 감사한 뒤 **같은 시험 재실행 없이** 다음 판단으로 이어간다.

**Cycle07 보고서는 L0/L2 원본 실측 후 갱신·커밋한다. G04B BLOCKED 유지.**


## 5. 원본 Gazebo 검증 결과 — Cycle 07 CLOSED / G04B BLOCKED

| 항목 | 실제 검증 |
|---|---|
| HEAD 소스 | `2cc479f025c6e4cf410e5c7e327caa31d6f63d9b` |
| GitHub PR 합성 체크아웃 | `8d3610c06c0d9cae345cb7b47939bc5aeeab0d41`; 양쪽 Git tree `f548f34755b78b2f3538e1a0a3af510b9e622756` 동일 |
| L0 | [#43770546088](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43770546088) SUCCESS |
| 실제 L2 | [#43770622882](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43770622882) **FAIL** |
| 원본 Artifact | **#14184565359**, 원본 ZIP SHA256 `b529217444359f86e4de17304824c30cc13e7cabac73bb6b9c9d54358ce1e423` |
| Bin sensor | `diag_bin_contacts.log` 4,219,931bytes; 실제 bin 접촉 이벤트 **5,371개** |
| 최초 접촉 | **sim 66.427초**, `g04_bin_support::bin_support::bin_collision` ↔ `my_robot::link4::link4_collision` |
| 접촉 위치 | 시작 [0.41424, 0.10002, 1.729997]m — bin 바닥 지지면 상단/모서리 부근 |
| High Goal 시각 | **64.798~67.828초** (접촉은 High Goal 진행 도중 처음 나타남) |
| 실제 물체 상승 / 1.3s drift | **0.11083m / 0.000498m** — 부분 성공 |
| 첫 실패 | `transfer_high_above_bin`: 목표 `joint1=0.423662rad`, 실제 오차 **0.219196rad**, `joint2` 오차 0.028768rad |
| 실제 joint2 명령·운동 | sim 66.427 전에는 native cmd/vel 둘 다 **0.05625rad/s**, 접촉 후 66.6초 cmd≈0.09022 vs actual vel≈0.03626, 68초 cmd≈0.27685 vs actual vel≈0.00191, 69초부터 cmd≈0.27492 vs 실제 vel≈0.0 |
| 하강·해제·ROI | **NOT_RUN**; high 추종 오류 발생 즉시 STOP |

### 인과 해석

이전에는 **bin support 접촉 자체가 실제로 발생하는지**가 UNKNOWN이었다. 이번 독립 bin sensor의 정확한 collision pair 및 시각은 이 공백을 해소했다. 접촉이 **high Goal 진행 중** 발생한 뒤 joint2 native 명령–운동의 불일치가 커진 시간적 선후관계는 일관된다. 물체가 아직 위에 있다는 사실이 robot arm link4와 bin의 부딪힘을 배제하지 않는다.

**원인 확정 범위:** '실제 link4↔bin support 충돌이 선행했고 joint2 tracking이 정체됐다'는 것은 원본이 지지한다. DART 제약의 힘·접촉 모델이 유일 원인이라고 단정하지 않는다. 기존 MoveIt planning scene에 동일한 static bin collision object가 있는지도 아직 검사되지 않았다.

### 개발 판단과 교육용 교훈

- 더 많은 FJT 명령·솔버·게인·마찰 변경보다 **실제 bin obstacle을 MoveIt PlanningScene에 등록해 OMPL이 충돌을 미리 고려하도록 하는 방법**이 먼저 검토할 단일 인과 수정이다.
- 로봇 부품이 목적지에 접근하는 경로도 필수 충돌 검사 대상이다. 그리퍼와 원통의 높이가 bin보다 높아도 팔 중간 link4는 bin 모서리에 접촉할 수 있다.
- 다음 Cycle08에서는 동일 bin collision shape/pose만 MoveIt planning scene에 추가하고, 계획 성공과 실제 native 비접촉 증거를 비교한다. 기존 Gazebo bin geometry/physics와 G04B 완주 인수 기준은 변경하지 않는다.
- 이번 Cycle07의 FAIL로 실험이 종료됐다. 이 원본을 다시 만들기 위한 즉각적 L2 재시험 금지.

**Cycle07 CLOSED / G00–G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## Cycle 07 실제 검증 결과 — CLOSED / G04B BLOCKED

- 코드 SHA `2cc479f025c6e4cf410e5c7e327caa31d6f63d9b`; 실제 Actions checkout `8d3610c06c0d9cae345cb7b47939bc5aeeab0d41`; Git tree 일치 `f548f34755b78b2f3538e1a0a3af510b9e622756`.
- [L0 #43770546088](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43770546088) PASS; [실제 Gazebo L2 #43770622882](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43770622882) FAIL.
- 원본 Artifact `14184565359`, ZIP SHA256 `b529217444359f86e4de17304824c30cc13e7cabac73bb6b9c9d54358ce1e423`.
- **원본 native bin 접촉 5,371개**: `g04_bin_support::bin_support::bin_collision` ↔ `my_robot::link4::link4_collision`. 최초 접촉 시뮬레이션 **66.427초**, 위치 [0.41424,0.10002,1.729997]m. High Goal 구간 **64.798~67.828초**, 따라서 이송 도중 실제 충돌.
- 실제 상승 **0.11083m**, 1.3초 hold drift **0.000498m**. High MoveGroup에선 `joint1` 목표 대비 **0.219196rad**, `joint2` **0.028768rad** 오차로 중단. 하강·해제·최종 안착 ROI **NOT_RUN**.
- native `joint2` 속도: 66.4초 CMD≈0.05625/actual≈0.05627rad/s; 접촉 후 66.6초 CMD≈0.09022/actual≈0.03626; 68초 CMD≈0.27685/actual≈0.00191; 69초 CMD≈0.27492/actual≈0.
- 결론: **link4와 bin의 실제 충돌이 고위치 이송 실패 이전에 발생**했다. 충돌과 제어 오차의 시간상 연관은 입증했지만 DART 내부 제약이 유일한 원인이라는 주장은 미확정.
- Cycle08 첫 구현 후보: 기존 static bin geometry/pose를 **MoveIt PlanningScene에도 동일 CollisionObject**로 등록. 실제 Gazebo geometry, 관절/물체/물리/안전 수용 기준 변경 금지.
- 반복 물리 실행보다 계획기 충돌환경 불일치부터 해소하는 **Architecture-First** 접근을 교육용 표준으로 보존.

**Cycle 07 CLOSED** / G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.
