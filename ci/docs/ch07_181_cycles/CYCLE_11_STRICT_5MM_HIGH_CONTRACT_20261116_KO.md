# G04B Cycle11 — strict 5mm high goal preflight and observation-cause separation
_2026-11-16 / Issue #181 / Draft #202; G04B BLOCKED_

## RED 원본

Cycle10 physical [#43788405858](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43788405858), Artifact #14191850785, ZIP sha256 `665a6b73bfdd82771c6453c5a2b3daa4412ecff44b882bb65b8a5b398355e164`; PR HEAD `1b6b9044112fed3c0e84e0b0e23754859cbf67b1`, 실제 checkout merge SHA `d95f75d51960d80c9556f816682f5a1df8317358`. 실제 50g rod lift `0.11841m`, hold `1.3s` drift `0.0013989m`, 실제 obstacle-aware high MoveIt 28-point path plan+execute 성공. 최대 native arm joint target error `0.00191845rad`로 0.01rad 범위 내. 하지만 **high goal ideal FK bin error `0.0204629m`**는 소스의 엄격한 **0.005m** 계약 위반. Native rod after high XY `0.022265m`. Lower/release NOT_RUN.

과거 공통 실패 문자열 `G04B_181_HIGH_MOVEGROUP_ACTUAL_JOINT_TRACKING_FAILED`은 실제 관절 추종 실패처럼 보였으나, 코드 `assess_precise_high_arrival`가 관절 오차와 목표 기하 오차를 **AND**로 검사했기 때문에 나온 포괄적 오류명이었다. 재현성 가설 검토 때 정확히 분리한다.

## 아키텍처 원인과 단일 수정

**실제 원본 고위치 Goal의 별도 5mm 계약**을 이전 Cycle10 기구학 후보 선택기의 25mm 조건이 놓쳤음. 속도/솔버/robot/bin/collision geometry/ROS Goal tolerance/5mm 계약 **변경 금지**.

- `ci/ch07_181_clearance_verified_high.py`: 원래 `HIGH_FK_BIN_TARGET_MAX_ERROR_M=0.005` 상수 자체를 import하여 SAT 분리≥3mm, 실제 held offset, jaw drift≤.25rad, 5mm target XY를 **동시에** 만족하는 후보만 반환하도록 fail-closed 전환. 기존 측정된 held state의 제한적 결정론적 탐색에서 후보 없으면 `C11_NO_HIGH_GOAL_WITH_ORIGINAL_BIN_AND_STRICT_5MM_XY`로 물리 Goal 전에 중지.
- `ci/tests/test_ch07_181_clearance_verified_high.py`: Cycle10은 SAT 통과·관절 성공이어도 exact 5mm는 FAIL임을 명시적 재현하고, 원본 scene/held offset으로 C11 후보 없음이 실제 ROS 없이 L0에서 드러남을 검증.
- `ci/ch07_77_g04b_actual_physics_witness.py`: 실제 joint 오차가 낮지만 목표 XY 5mm가 넘은 경우 물리 오류명을 `G04B_181_HIGH_SOURCE_FK_GOAL_GEOMETRY_OVER_5MM`로 구분. 본 사이클은 새 MoveGroup/관절 실제 동작 없음.

이 실패는 **현재 제한 탐색에서 새 목표가 없음**을 의미한다. 전역 기구학적 불가능성의 수학적 증명은 아니다. 따라서 새로운 물리 시험으로 문제를 숨기지 말고, 독립적인 원본 모델의 기구학/장애물 접근 구조를 분석하여 진짜 5mm 충돌 없는 goal을 증명해야 한다. 해당 증명이 되기 전 Owner/물리 L2 호출 보류.

## 독립 오프라인 진단과 인수 경계

- 원본 source-geometry continuous SLSQP 보조 진단(프로덕션 의존성 아님)은 기존 실제 held offset·원래 bin, XY≤0.005m·jaw≤0.25rad·tool angle≤0.38rad·high≥1.98m 하에서 약 **-0.0017m**(box overlap)에서 수렴. 탐색 초기값을 바꾼 여러 시도도 같은 국소 경계로 수렴했으나 **global infeasible 판정 아님**.
- 반면 Cycle10 SAT≥+0.0073m 후보는 source 5mm XY gate에 실패. 두 제약의 상충을 확인. 예전 high 25mm ROI 성공과 완전한 5mm 물리 placement 인수는 다르다.
- **절대 금지:** 5mm→25mm 완화, native bin 삭제·형상 축소를 통한 인위적 Green, 실제 rod teleport/force attach.

## 교육용 교훈

테스트가 `JOINT_TRACKING_FAILED`로 보이더라도 반환된 복합 predicate의 각 조건을 분리하여 최초 원인(잘못된 목표 선택)을 확인한다. ROS/Gazebo 비싼 재시도보다 기존 Artifact를 감사하고 오프라인 가설을 먼저 반증한다.

**L0:** 후속 Run ID로 확정 기록. **물리 L2:** NOT_RUN (새로운 실제 목표 없음). **G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## Cycle11 실제 L0 검증 종료

- [G04B L0 Run #43790029897](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43790029897) **SUCCESS**, `dynamic-physics-grasp-only` **SKIPPED**.
- [Book Lab Run #43790029886](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43790029886) 일반 문서 경로에 해당. 물리 L2 재실행 없음.
- Cycle11 패치 커밋 `1480775ce9a12c2399bd2706c5278f7259b0c22b`; 이후 summary-only CI 수정 별도 `671e289c4129c6ad5a90298f674a213be3262ca0`.
- 실제 bin을 유지한 C11 제한 탐색에 충돌 없는 5mm 후보가 없음을 조기 중단으로 표현하며, *모든 설계가 불가능하다는 증명은 아님*. 다음 아키텍처 실험은 원본 형상 유지 + 물리적 설치 방향 한 가지만 변경한 새로운 시험 fixture로 취급해야 함.
