# G04B Cycle 03 — DART contact PGS solver 단일 물리 비교

- 날짜: 2026-11-15 / Issue #181 / Draft PR #202
- 기준 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`, 기준 코드 `11090b223daa74aea5beb3dfa4c8040306d451ba`
- 고정 원본 동적 물리 FAIL: [#43719033640](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43719033640), Artifact #14164070632 ZIP SHA256 `96362eace97d021acfeb47979f35d2fefcd516054547d0b937213e97fbe211e5`
- 이전 Cycle 01/02: high joint2 최종 0.0130665rad 오류, high 종료+0.2~+0.7초 native cmd median 0.123818rad/s, 실제 velocity median 0.000140rad/s. **G04B BLOCKED**.

## RED 및 가설

원래 DART Dantzig contact constraint solver를 사용하는 현행 앵커 고정 테스트 월드에서, 실제 50g 원통 물체를 잡고 운반할 때 joint2 velocity command 대비 물리 운동이 정체된다. **가설:** DART 접촉 제약 solver 방식이 이 말기 오차의 원인일 수 있다. 기존 Draft #197에서는 다른 구동 기준선에서 PGS가 물체 custody에 개선을 보였지만 완주 FAIL; 현행 SHA에 성공 근거를 이전하지 않는다.

## 변경 요인 단 하나

이미 검증했던 Draft #197의 `ci/ch07_181_dart_solver_single_factor.py`와 negative TDD를 재사용한다. `world/physics/dart/solver/solver_type = pgs` 필드만 test-only world SDF에 추가. XML equality로 다른 요소의 변경을 거부한다. 원본 DART 충돌 검출 ODE, 1ms physics step, world gravity −9.8m/s², 50g 동적 원통, 마찰, ROS 7개 관절/컨트롤러, finger test-only 하한 −0.001m 및 world anchor, ROS Goal, 물리 안전 판정은 모두 동일하게 유지한다.

## 개발 결과물

- 코드: `ci/ch07_181_dart_solver_single_factor.py`, `ci/ch07_77_g04b_physical_once.sh` (한 세계에서 한 요인)
- 단위 테스트: `ci/tests/test_ch07_181_dart_solver_single_factor.py` (질량·중력·검출기·기타 물리 변환 금지)
- GitHub Actions: 관련 소스 SHA와 L0 테스트, 승인형 Gazebo 물리 Job 유지
- **L0: SUCCESS #43720961400 / L2: FAIL #43721071561 / Artifact: #14163978713**

## 1회 검증과 중단 조건

L0 성공 시 **동일 SHA 승인형 Gazebo L2를 한 번** 실행. PGS 조건에서 실제 joint2 고착과 원본 native 물체 최종 배치 여부 확인. 실패하면 G04B BLOCKED 유지, 동일 solver를 다시 시험하지 않고 원본을 감사해 다음 실패만 추출한다. 물체 teleport/attach, Goal 허용오차 확대, 가짜 접촉, 기존 성공 결과 재실행 금지.

**교육 목표:** 이론적 solver 대안이 실제 인수 오류를 해결하는지는 하나의 물리 요소만 바꾼 A/B 실험으로 검증한다. 통과하지 못한 실험을 억지로 PASS로 만들지 않는다.

## Cycle 03 실측 결과 및 최종 판정 — CLOSED

| 항목 | 원본 증거 및 결과 |
|---|---|
| 승인형 L0 | [#43720961400](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43720961400) **SUCCESS**, 실제 Gazebo SKIPPED |
| 승인형 L2 | [#43721071561](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43721071561) **FAIL** |
| 실행 원본 Artifact | **#14163978713**, GitHub ZIP SHA256 `b8e2a0bbb99accef578047e714819ff25ad8abce261baeb9e76b824fdbdfbd44` |
| PR HEAD | `98abded498bd94a65e0a382ad69aed95c9532797` |
| 실제 CI checkout | `52685f7f2723d43cd7b17406f8780969a950b9f4`; GitHub PR 임시 merge (parents: `1aadc7553a97cfacec1ebeca007910905c228a92` + PR HEAD); **git tree SHA `7fcedef98933dbeef5f13a177ffd7b6d20a0c94b` 동일** |
| DART 변경 영수증 | `world/physics/dart/solver/solver_type=pgs`, 다른 fixture/world 요소 변경 없음, 50g 동적 물체, 원본 gravity·friction·목표·tolerance 불변 |
| 두 손가락 실구동 | 각각 약 1.90mm 실제 `FJT SUCCEEDED` |
| 실제 물체 상승/hold | 상승 **0.11424m**, 1.3초 후 drift **0.00033625m** |
| high 운반·상단 정렬 | 실제 custody drift **0.00301568m**, bin XY 오차 **0.01243454m**, high arm target 최대 오차 **0.00854880rad** (0.01rad 이내) |
| 첫 실패 단계 | **`lower_into_bin`**, MoveGroup status4·MoveIt error1이지만 실제 `joint3` 오류 **0.13136950rad** |
| 이어진 단 1회 엄격 FJT | `status=6 ABORTED`, `result=-5`, 목표 `joint3=1.254839883790849rad`, 실제 **1.128603878917686rad**, 오차 **0.12623600rad** (엄격 0.01rad 불충족) |
| 해제·안착 ROI | **NOT_RUN** — arm Goal 9, gripper Goal 3, 실패 즉시 종료, SIGKILL 없음 |

### 물리 가설 판단

1. 기본 Dantzig의 high 관절2 추종오차는 앞선 다른 cold run에서 0.011~0.013rad였고, 이번 PGS 시험의 high 관절2 오차는 0.00855rad로 범위 내였음. **단 1회씩 다른 cold run 비교만으로 PGS가 안정적으로 high 문제를 해결했다고 입증할 수 없음**.
2. 더 중요한 **완주 G04B의 첫 미충족 항목은 PGS에서도 `joint3` 하강 목표(0.126236rad 차이)**. 동일 물체가 진짜 올라가고 유지됐으므로 finger 초기 failure는 아님.
3. 기존 Dantzig physical [#43712237998](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43712237998) 역시 하강 `joint3` 오차 **0.134865rad**. **PGS 단독 물리 인수 해결 가설 기각**. 다인자 솔버·마찰·게인 sweep은 하지 않는다.
4. 관절3은 원본 URDF 한계 `[-2.0944,+2.0944]rad`로, 목표 `1.25484rad` 자체가 명시적 관절 한계 위반은 아님. 그 외 실제 충돌/제약/컨트롤러 명령 중 어느 것이 하강 정체를 일으켰는지 아직 근거 부족.
5. 시험 결과를 반영하여 **PGS를 물리 world에 주입하는 활성 호출은 원복**. 수동 단일 요인 변환 스크립트·음성 테스트는 교육/재현용으로 보존하지만, 기본 경로는 기존 검증 world 솔버로 복귀.

### 교육용 디버깅 기록

- *실패 관측*: MoveIt Goal이 SUCCEEDED라도 실제 joint3가 0.13rad 미도달한다.
- *가설*: contact solver를 PGS로 변경하면 말기 서보 제약이 풀릴 수 있다.
- *실험*: SDF에서 solver 한 값만 바꾸고 native 물체와 실제 FJT를 동일 기준으로 실행.
- *반증*: 높은 곳 운반은 통과했으나 하강 직접 FJT에서 동일 유형의 관절 고착이 반복되었다.
- *의사결정*: **후보 원복** 및 다음 실패 경계 계측으로 이동. 테스트 횟수를 늘려 통계적 성공을 가장하지 않는다.
- *다음 Cycle 04*: 고정된 원본 ZIP으로 `joint3` 명령·물리·충돌의 기존 증거를 감사하고, 빠진 명령/실제 joint3 관측만 최소 추가. 새 인과 정보가 없으면 실제 Gazebo 재시험 금지.

**최종 판정:** Cycle 03 CLOSED / **G04B BLOCKED, G05 NOT_RUN, Ch10 HOLD**, 기존 G00–G04A PASS 증거 NOT_RERUN. 보고서 수정 커밋 자체는 실제 CI source SHA와 달라서 그 실험의 full G04B PASS를 주장하지 않는다.
