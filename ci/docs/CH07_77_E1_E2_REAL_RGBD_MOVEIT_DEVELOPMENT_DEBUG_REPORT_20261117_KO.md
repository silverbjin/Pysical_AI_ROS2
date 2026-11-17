# Ch07 §7.7 E1/E2 실제 RGB-D→MoveIt 계획 통합 개발·디버깅 최종 보고
_2026-11-17 | 통합 개발 Draft PR #204 | 전체 물리 인수는 아직 BLOCKED_

## 1. 범위와 결론

**실제 Gazebo Harmonic OGRE2 RGB-D**에서 검출한 동적 빨간 24mm 원통의 픽셀+Depth+CameraInfo+촬영시각 TF를 `base_link` 3D 목표로 변환하고, **기존 G01 one-shot**을 통과한 PointStamped로부터 실제 **MoveIt `/move_action` 계획 3개**를 계산했다. 최종 승인형 공개 CI [Run #43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) **SUCCESS**, Artifact [#14249512043](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590/artifacts/14249512043); 원본 ZIP SHA256 `3958f196553a294212225889a02f5f7633a1d90390ed19ed1305eea54c7f1ecc`. 전체 `result.json`은 `rc=0`, `OWNED_GROUPS_EXITED_NO_SIGKILL`, 원래 Gazebo **natural rc=0**.

**승인 범위는 `E2_SENSOR_TO_MOVEIT_PLAN_ONLY=SCOPED_PASS` 하나**이다. MoveGroup의 `planning_options.plan_only=true`; arm/gripper motor Action Goal 전송 **0**. Native physical grasp/lift/hold/transport/release/ROI **NOT_RUN**. 이전 G04B 19사이클의 충돌 문제는 `G04B_PHYSICAL_CLEAN=BLOCKED`, 전체 §7.7 `CH07_77_E2E=BLOCKED`, G05 NOT_RUN, Ch10 HOLD, Owner WSL2 NOT_READY.

**실제 소스:** 원격 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`에서 새 분기 `plan/ch07-77-rgbd-moveit-physical-e2e-20261117`로 개발. CI의 실제 실행 receipt `source_sha=b14d863e422112a2718e08f4675ccd3f229f6372`는 GitHub PR의 **merge checkout SHA**이며, PR 소스 HEAD `ebbfa9ecfeae761616468e32769d73b0197df453` (R3 시점)와 다르다. 이 차이를 섞거나 source invariant 위반으로 무시하지 않는다. 이후 guide/CI 비용 제어 커밋은 R3 물리 실행 코드가 아니라 문서/dispatch 정책이다.

## 2. 기검증 성과 재사용 및 신규 최소 구현

| 영역 | 재사용 또는 개발 범위 | 계약 |
|---|---|---|
| 실제 센서 | 이미 성공한 G04A의 실제 `object_detector`, `coord_transformer`, `mission_controller` 및 `ci/ch07_77_g04a_graspable_fixture.py` | 가짜 depth/월드 목표 재생 없음, 같은 촬영 시각의 RGB+Depth+K+TF |
| G01 one-shot | `mission_target_gate.py`의 두 프레임 안정성·timestamp/frame/workspace/finiteness 검사와 `/ch07_77/target_ready` 재사용 | 중복·불량 입력 신규 실제 Goal 0 |
| **E1 신규** | `mission_geometry.py`: 읽기 전용 surface XYZ→test fixture wrist XYZ→원래 5DOF analytic **position** IK 후보 `pregrasp/approach/grasp` | 원통 하나·fixture 전용, 6DOF orientation IK/실제 TCP 파지 검증 주장 금지 |
| **E2 신규** | `mission_plan_only.py`, `setup.py` entry: 유효한 센서 좌표로부터 `MoveGroup.Goal` 실제 request 3개 | `plan_only=True`, 모터 Action 0. 기본은 observe, execute 모드 없음 |
| **실제 단일 세션 실행** | `ci/ch07_77_e2_rgbd_moveit_plan_once.sh` (G04A 원샷 기반) + `book-ch07-77-e2-live-plan-once.yml` | 기존 Jazzy/Harmonic digest 재사용, ROS/Gazebo 같은 세션, 정확한 receipt와 종료 rc |
| L0 / 강의 | `ci/tests/test_ch07_77_e2_sensor_moveit_contract.py`의 6개 수치·fail-closed 검사; `Ch07/docs/LAB_7_7_E2_REAL_SENSOR_MOVEIT_PLAN_ONLY_KO.md` | 학습용 원본 코드 리뷰, ROS·Gazebo 없이 선택적 단위 시험 |

**이미 성공한 G00~G04A의 독립 수락 시험을 변경/재인수하지 않았다.** 통합 원샷의 실제 센서 관측은 새 **E2 연결 경계**를 검증하기 위한 동일 세션이라 별도 필요하다. 물리 Draft PR #202는 이번 브랜치에 복제·병합하지 않았다.

## 3. 실제 E2 수치·원본 증거

[Run #43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) 원본 `e2_moveit_plan_receipt.json`:

```text
source_sha (PR merge checkout): b14d863e422112a2718e08f4675ccd3f229f6372
actual G01 target stamp: 17.755s; frame=base_link
actual 3D sensor xyz(m): [0.7880663657,0.0013493681,1.9429922527]
candidate pregrasp wrist(m): [0.4980663657,0.0013493681,1.8529922527]
candidate approach wrist(m): [0.5680663657,0.0013493681,1.8529922527]
candidate grasp wrist(m): [0.6380663657,0.0013493681,1.8529922527]
MoveGroup plan_only (3 stages): all STATUS_SUCCEEDED(4), MoveIt SUCCESS(1)
planned_points: [57,57,57]
arm_motor_goal_count=0; gripper_motor_goal_count=0
result.json: SCOPED_PASS, rc=0, owned shutdown clean
native Gazebo natural exit rc=0
```

동일 원본 `g04a_live_receipt.json`: RGB Image **32**, Depth **15**, CameraInfo **40**, 실제 detector pixel **4**, 3D target **2**, ready **1**, joint_state **227**. `target_pixel.point.z`는 contour area, Depth가 아니다. 실제 `ready`와 3D stamp **17.755** 일치. 독립 audit은 pixel stamp-3D source log-G01 ready-E2 request의 **동일 3D 좌표와 시각**을 원본으로 대조했다.

## 4. 개발–실패 분석–수정 사이클 (교육용)

| 사이클 | Run | 관측 | 최초 실패와 처리 |
|---|---|---|---|
| L0 | [#43910415763](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43910415763) | 신규 6개 단위 시험 PASS; 다른 센서 위치→다른 IK 목표, 부적합 입력 reject, plan_only/source-only | L0는 Gazebo/물리 PASS가 아님 |
| Live R1 | [#43911395629](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43911395629), Artifact #14247263183, ZIP `7f4810ea4d6ddc99db0076507c7c971af754df73e643b067210990d2ebd7f6cf` | 실제 RGB-D·G01·MoveIt 58/58/57점 세 단계 **기능 성공** | 유한 시뮬레이션 `--iterations=80000` 후 원본 종료에서 Gazebo `SIGKILL_ESCALATION`, rc75. **Run FAIL 유지**; 이미 검증된 G04A finite 25000회로 원복 |
| Live R2 | [#43912441624](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43912441624), Artifact #14247818004, ZIP `969513a93c24c77bd792c53afc6d5d8dc0940fc4793948bc143f83d2a4cda090` | E2 MoveIt 계획 3개 **성공**, 실제 G01 ready stamp16.369, xyz ≈(0.788066,0.001349,1.942992) | 기존 G04A 관찰기가 stamp16.369의 3D 메시지를 놓치고 16.732 이후 샘플만 보유하여 `MISSION_TARGET_NOT_FROM_SENSOR` FAIL. 같은 첫 시각의 **원본 `coord.log` 3D 출력과 G01 ready가 일치**한 것을 오프라인 확인 |
| Live R3 | [#43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590), Artifact #14249512043, ZIP `3958f196553a294212225889a02f5f7633a1d90390ed19ed1305eea54c7f1ecc` | 실제 센서·G01·MoveIt 57/57/57점, 원본 pixel/3D/G01/E2 인과 조인 **PASS**, 정상 종료 rc0 | **E2 scoped accepted**. 기존 witness가 미수신한 표본을 가짜로 채우지 않음; 실제 `coord.log` + raw pixel + ready + planner target으로 독립 cross-check |

**CI 운영 수정:** `Book Lab Acceptance`의 기존 `unittest discover -s ci/tests -v`는 문서용 sparse runner에서 `vision_basics`를 찾지 못하고 G01/E2 ROS 시험을 잘못 import하여 Red가 반복됐다. 승인된 프로세스 Draft #203의 선택적 CI 원칙대로 PR #204에서 **문서 validator 2종만 실행**하도록 분리, Book Lab 후속 #43914946467 SUCCESS. 변경 파일마다 PR에 누적된 workflow path로 실제 Gazebo가 자동 중복 실행되는 경계를 발견해 **`ch07-e2-live-once` 라벨 이벤트 또는 명시적 수동 dispatch에만 비싼 live E2 Job을 승인**하도록 변경했다. 새로운 무단 물리 모터 Goal은 계속 0.

## 5. 다음 물리 E3에서 반드시 먼저 해결할 문제(새 L2 미실행)

1. **계측 기반 형상 보정:** 이번 G04A 실제 rod world center는 x≈**0.80m**인데 C17 G04B 별도 시험 rod world center는 x≈**0.70m**. E2 `FixtureCalibration`의 `surface_to_wrist_x=-0.15m`은 이종 fixture 경험값을 바탕으로 만든 **계획용 초기 후보**이므로 물리 파지 적합성을 보장하지 않는다. 기존 C17 native 손가락 충돌 중심≈(0.70105,0,1.92138)m at wrist pregrasp≈x0.63을 현재 G04A world x0.80에 그대로 적용하면 물체와 약 0.10m 어긋난다. 실제 카메라·원통·동일 robot base가 한 월드에 있는 조건에서 surface→rod center→jaw collision center→TCP 오프셋을 먼저 **독립 측정**하고 고정한다.
2. **world 기구 차이:** 현재 G04A의 원래 robot spawn z=+0.05m, #202 G04B 실제 물리 test-only spawn world fixed base z=0, test-only bin yaw=0.35rad. 원본 yaw0 또는 현재 G04A fixture와 동일 성공으로 전이 불가. 단일 E3/E4 통합 월드에서 원래 센서/컨트롤러와 실제 파지 테스트월드를 **하나의 정확한 모델/좌표계**로 고정해야 한다.
3. **손목–원통 진짜 충돌:** G04B C17/C18/C19 각각 native 충돌 **648/620/535건**, C19 settled XY error **0.13708m**(한계0.09m), C17 성공 배치라 해도 무충돌 FAIL. 속도 sweep 재개 금지. 이전 native C17 pre-release rod≈(0.503606,0.238149,1.91499)m와 settled≈(0.55292,0.292337,1.742)m를 포함해 **해제 전 wrist 위치·낙하 구간의 상대 clearance**를 같은 world/sim timestamp로 재설계. 오프라인 후보가 제시되고 MoveIt FCL 안전 계획 및 사용자 허용 L2 이벤트가 있을 때만 물리 한 번.
4. **E4 전체 인수 금지 유지:** E3 native 양측 force·lift≥5cm·hold≥1s·release·XY≤9cm·높이≤5.5cm·금지 손목 충돌0이 없으면 센서→모터→물체 실제 이동의 **동일 세션 E4 SCOPED_E2E_PASS** 불가. 이후 E5 Owner WSL2는 NOT_READY.

## 6. 실습용 보고·출판 메모

- 교재에서 **MoveGroup 계획 SUCCESS ≠ 실제 움직임 SUCCESS ≠ 물리 파지 SUCCESS**를 실제 L0/Live R1~R3 수치로 비교한다.
- `mission_plan_only`는 별도 `mission_controller`를 대체하지 않는다. upstream G01에서 본 `target_ready`만 소비하며 잘못된/stale 입력, 불가능한/미승인 fixture는 Goal 전 차단.
- 순수 수치와 contract는 선택적 TDD, ROS topic↔MoveGroup은 단일 실제 Gazebo scoped integration, 물리 접촉은 추후 한 번의 명시적 L2. 합격한 G00~G04A 독립 시험은 다시 인수하지 않는다.
- 교재용 [E2 실습 가이드](../../Ch07/docs/LAB_7_7_E2_REAL_SENSOR_MOVEIT_PLAN_ONLY_KO.md)와 이번 보고서는 코드를 읽으며 개발·분석·디버깅의 단계별 증거를 설명하기 위한 기록이다.
- `Ch07/docs/LAB_7_7_GUIDE_KO.md`의 옛 문장은 아직 G01이 존재하지 않는다고 기술하므로, §7.7 **전체 인수 전** 실제 구현에 맞게 정정해야 한다. 현재 총괄 교재 인수는 계속 BLOCKED.

**정식 범위 판정:** `E1/E2=SCOPED_PASS` / `G04B_PHYSICAL_CLEAN=BLOCKED` / `CH07_77_E2E=BLOCKED` / `G05=NOT_RUN` / `Ch10=HOLD` / `Owner_WSL2=NOT_READY`.
