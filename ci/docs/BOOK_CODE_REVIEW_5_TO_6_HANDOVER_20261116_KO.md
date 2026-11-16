# 도서코드검수_5 → 후속 작업 인계 (2026-11-16)

> 기준: 원격 main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`; 활성 G04B 개발 Draft PR [#202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202); Issue [#181](https://github.com/silverbjin/Pysical_AI_ROS2/issues/181); 별도 프로세스 Draft [#203](https://github.com/silverbjin/Pysical_AI_ROS2/pull/203). 아래 SHA는 이 문서 작성 전 확인된 시점 기준이다. 새 작업 때 원격 재조회.
>
> **인수 판정: G00~G04A 기존 성공 NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.** G04B 미완료를 L0·MoveIt 계획 성공만으로 승격하지 않는다.

## 1. 이전 작업 복원과 실제 중단 지점

- 원격 main은 위 SHA 그대로이며, G00~G04A 승인 결과는 보존한다. 원래 Draft #180 등 선행 PR들은 병합·삭제하지 않는다. 활성 물리 개발은 #202 단일 PR로 잇는다.
- 실험 기록: `ci/docs/ch07_181_cycles/CYCLE_01_*.md` ~ `CYCLE_09_ALTERNATE_ELBOW_HIGH_20261116_KO.md`; 독립 원본 로그는 해당 각 문서의 Run/Artifact/SHA256에 고정되어 있다.
- 최신 실제 L2: [Run #43781963845](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43781963845), 소스 `a2678219c3253fdf70c760666848277e62216bad`, Artifact **#14188569056**, 원본 ZIP SHA256 `076bf90754e09a7a39dd3d23672681ceb191b43130ed8083a6bab46b15d0e87c`: **FAIL**, 성공 아님.
- 같은 실험에서 50g 동적 rod 실제 상승 `0.14509m`, 1.3s hold drift `0.00077469m`. Gazebo 원래 bin [0.55,0.25,1.63]m / box [0.30,0.30,0.20]m를 MoveIt PlanningScene에 올리는 작업은 SUCCESS.
- **최초 실패**: high arm 목표가 실제 bin과 **link4 충돌**. 기존 양의 팔꿈치 분기, Cycle09 음의 팔꿈치 분기 둘 다 OMPL `Unable to sample any valid states for goal tree`; `plan_only` `ABORTED`/`planned_points=0`, 위험한 real high Goal 미전송. 하강·해제·정착 NOT_RUN.
- 최신 #202 HEAD `d61a4a767cb41ebf4d20a9b8380e70daed93077d` (Cycle09 보고서 마감), [L0 #43782501728](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43782501728) SUCCESS, **L2 SKIPPED**. 따라서 실제 최종 인수는 위 L2 실패 기록을 따른다.

## 2. 승인된 효율적 개발·디버깅 표준 (기존 TDD 전면 적용을 교체)

**최상위 승인본:** `ci/docs/BOOK_ROS2_DEVELOPMENT_DEBUG_CI_EXECUTION_STANDARD_20261115_KO.md` (프로세스 Draft #203, `BOOK_ROS2_DEV_DEBUG_CI_STD_V1`). 간략 운영판 `ci/docs/BOOK_REVIEW_FAST_LOOP_STANDARD_20261115_KO.md`.

1. **Architecture-First**: 로봇의 원본 Xacro/URDF/SDF, world↔model↔link 변환, Controller/MoveIt/Physics 제어권과 진짜 장애물 형상 및 성공 판정기를 먼저 검증한다. 원본 `world_to_base_joint`는 주석 처리; test-only SDF에만 정식 world fixed base를 적용한다.
2. **Evidence-First**: 원본 immutable Artifact의 최초 불일치 1개만 좁힌다. native Gazebo model/link world pose는 SceneBroadcaster model-relative pose와 다르므로 정확한 변환·시간 정합을 증명한다.
3. **선택적 TDD**: 반증 가능한 가설 하나, 변경 요인 하나, 예상 관측/중단 조건 하나. 관련 L0 단위시험만 실시; ROS 인터페이스를 바꿀 때만 L1을 추가한다. 동일 실패 2회/새 정보 없음이면 STOP하여 판정기·계측·기구학을 다시 조사한다.
4. **승인형 실제 Gazebo L2**: L0/L1 통과 이후 단 1회 공개 CI 물리시험. PR `synchronize`는 **L0 전용**, 새 `g04b-physics-once` 라벨 이벤트에서만 L2. 실제 강사/Owner WSL2는 마지막 인수만 한다.
5. **원본 증거·정확한 상태**: source SHA, Docker digest, Run/job, 원본 ZIP/SHA256, joint desired/feedback/error, native pose+contact, 실제 rod lift/hold/carry/placement ROI, 종료 상태 기록. `Action SUCCEEDED`, 양성 force, 초록색 L0만으로 물리 PASS 불가.
6. **Review/Report/Commit**: 매 사이클 `ci/docs/ch07_181_cycles/CYCLE_XX_..._KO.md`에 RED→원인/가설→변경 한 가지→L0/L1→L2 원본/최초 실패→결론·교육 포인트를 남겨 소스와 함께 커밋한다. Issue #181과 #202에 증거를 연결한다.

**금지:** 이미 PASS인 G00~G04A 재실행, fake attach/rod teleport/관절 상태 조작, bin 충돌 은폐, 물리 판정 임계치 완화, 원인 없이 솔버/속도 sweep, 새 Draft PR 난립, 승인 없는 main 병합, Ch10 변경.

## 3. 다음 최소 실험 — Cycle10

**진단된 구조:** 원본 Xacro `link4`는 0.5m 길이·폭 0.05m 충돌 상자. 실제 bin은 box [0.30,0.30,0.20]m. 기존 high 두 목표는 link4가 bin을 관통한다.

**가설:** 기존 bin/URDF/물리/수용 임계치를 **그대로 유지한 채** high의 최종 5DOF 목표 자세만 선택적으로 재구성하면, 원래 로봇 기구학과 세계 좌표에서 충돌 없는 방향을 찾을 수 있다. 반드시 고정된 50g 실제 rod의 measured held offset과 양측 grip world jaw 방향을 반영한다.

**반증 게이트:** original box geometry의 보수적 OBB SAT 검사 → 독립 MoveIt 원래 PlanningScene `plan_only` → (L2 승인 시) 실제 MoveGroup → native contact/rod custody. SAT 통과는 단지 후보이며 FCL 계획 및 Gazebo 성공 아님. 기하학적 후보가 없거나 계획 실패면 real high Goal 금지·G04B BLOCKED.

**Cycle10 이전 상태:** 최초 실패는 Cycle09의 collision-checked high `plan_only`. G04B 전체 완료는 아직 입증되지 않았다. 후속 실험에서도 실제 하강/해제/정착까지 충족해야 전체 PASS.

## 4. 즉시 실행 가능한 작업 순서

1. 원격 `main`/#202/#203, 최신 L2 Run/Artifact/소스 SHA를 재조회하고 해당 시점 유지.
2. `ci/ch07_181_exact_fk.py`, `ci/ch07_181_jaw_axis_carry.py`, `ci/ch07_181_collision_free_high_branch.py`, `ci/ch07_181_bin_moveit_scene_contract.py`, `ci/ch07_77_g04b_actual_physics_witness.py`, `ci/ch07_77_g04b_physical_once.sh`와 Cycle09 raw를 참조.
3. Cycle10 high clearance 단일 변수 알고리즘을 오프라인으로 입증하고 집중 TDD. bin 충돌 형상·수용 기준 수정 없음.
4. L0 성공하면 새 승인형 L2 1회만 시도. Artifact 원본 감사를 기록한 뒤 실패 원인에 맞춰 Cycle11 착수. **무한 재시도 금지**.
5. 실제 high→lower→release→settled ROI와 native bilateral contact 전체 성공이 독립 확인될 때만 G04B PASS 검토. G05는 별도 후속, Ch10은 HOLD.

## 5. 새 대화 시작용 프롬프트

`ci/docs/BOOK_CODE_REVIEW_5_TO_6_HANDOVER_20261116_KO.md`와 승인 표준 `ci/docs/BOOK_ROS2_DEVELOPMENT_DEBUG_CI_EXECUTION_STANDARD_20261115_KO.md`를 먼저 읽어라. `silverbjin/Pysical_AI_ROS2` 원격 main·Draft PR #202 및 프로세스 PR #203의 최신 HEAD, Issue #181, 최신 L2 원본과 SHA를 대조하라. G00~G04A 성공 재실행 금지, G05 NOT_RUN, Ch10 HOLD. Cycle09의 실제 MoveIt bin↔link4 collision 최초 실패부터 **Architecture/Evidence-First + 선택적 TDD + L0→승인형 공개 Gazebo L2 단일 시험**으로 G04B만 해결하라. 가설/첫 불일치/반증/원본 CI Artifact/교육용 결론을 매 사이클 보고서와 코드에 함께 커밋하라. 물리 원본 전체 성공 전 G04B PASS 또는 Owner WSL2 READY를 선언하지 마라.
