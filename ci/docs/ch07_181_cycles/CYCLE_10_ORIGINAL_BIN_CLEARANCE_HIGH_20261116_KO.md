# G04B Cycle10 — 원본 bin 충돌 상자에 대한 고위치 목표 자세 재설계
_2026-11-16 / Issue #181 / Draft #202_

## RED / 원본

직전 승인형 실제 Gazebo [#43781963845](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43781963845), Artifact **#14188569056** (ZIP sha256 `076bf90754e09a7a39dd3d23672681ceb191b43130ed8083a6bab46b15d0e87c`): 50g rod **실제 상승 0.14509m**, hold drift **0.00077469m**, 실제 static bin을 적용한 MoveIt 고위치 자세는 원본 0.5m `link4`와 **충돌**하여 plan_only ABORTED. 원래 +elbow 및 Cycle09 -elbow 모두 high real Goal 이전에 차단. 하강·해제·정착 NOT_RUN.

## 한 가설 / 변경 한 가지

다른 솔버/속도/충돌 물체/ROI 허용오차를 건드리지 않고, **high 단계의 목표 관절 자세만** 바꾼다. 기존 Xacro link4 박스 0.05×0.05×0.5m, 원본 Gazebo bin 박스 0.30×0.30×0.20m at (0.55,0.25,1.63)m와 test-only fixed-base world 변환을 정확히 계산한다. 실제 held 50g rod offset을 반영하는 결정론적 제한 탐색으로 원래 bin 내 high XY≤0.025m·height≥1.98m·world jaw drift≤0.25rad를 만족하는 후보를 찾는다.

## 코드/불변식

- `ci/ch07_181_clearance_verified_high.py`: 3D OBB SAT; 충돌 상자는 전혀 변경하지 않음. SAT 분리는 **후보만** 의미하며 MoveIt/FCL 또는 물리 PASS 증거가 아님.
- `ci/tests/test_ch07_181_clearance_verified_high.py`: 이전 양/음 팔꿈치 목표의 실제 상자 교차와 raw held offset 신규 후보, scene/bin 조작·NaN·물체 미파지 방지.
- `ci/ch07_77_g04b_actual_physics_witness.py`: **명시적 C10 flag**일 때만 후보 목표를 적용. 반드시 실제 MoveIt `plan_only` 통과 후에만 real high goal.
- 고정 Docker digest, original Gazebo bin/URDF/solver/contacts/Goal tolerance/lift·hold·release·settled ROI 게이트 모두 보존. Fake attach, rod pose overwrite, collision disable 없음.

## 검증·회고

L0와 승인형 L2 Run/Artifact는 뒤이어 원본 조회 후 이 문서에 기록한다. 후보 탐색의 기구학적 수치만으로 **G04B PASS 불가**.

교육 포인트: 원래 구조의 OBB와 실제 월드 장애물의 3D 교차를 검증한 뒤 목표 *자세*를 수정한다. 물리 충돌을 무시한 MotionPlanner 재시도는 문제를 은폐할 뿐이다.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY**.

## 2026-11-16 실제 원본 L0→L2 감사 — Cycle 10 CLOSED / G04B BLOCKED

- Cycle10 PR HEAD `1b6b9044112fed3c0e84e0b0e23754859cbf67b1`; 실제 `pull_request` Actions checkout merge commit `d95f75d51960d80c9556f816682f5a1df8317358` — **둘을 혼동하지 말 것**.
- 공개 G04B L0: [#43788323615](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43788323615) SUCCESS. Book Lab L0: [#43788323620](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43788323620) SUCCESS.
- 신규 라벨 이벤트 승인형 실제 Gazebo L2: [#43788405858](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43788405858) **FAIL**; Artifact **#14191850785**; ZIP SHA256 **`665a6b73bfdd82771c6453c5a2b3daa4412ecff44b882bb65b8a5b398355e164`**. 런타임 기존 GHCR `sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`.
- 실제 50g rod 상승 **0.11841m**; 1.3s hold 동적 world-pose 변동 **0.00139890m**. 실제 bin 원래 shape/pose `/apply_planning_scene` SUCCESS, 세션 original native ROS/Gazebo 및 실물체 유지.
- **중대한 개선:** 새 high goal `joint1=0.42525871, joint2=0.06, joint3=0.468, joint4=1.23086970, wrist=0`의 원본 `link4`↔bin SAT separation **+0.00730558m**. MoveIt 실제 FCL `plan_only` **SUCCEEDED, 28 points**, 이어 실제 high MoveGroup **SUCCEEDED, 28 points**. 이전 Cycle08/09의 목표 충돌 BLOCK이 **현재 목적지/계획경로 범위에서 해소됨**.
- 원본 high 이후 actual joint-state 최대 목표 오차 **0.00191845rad**, 계약 최대 `0.01rad` 이내. **관절 구동 실패가 아님**.
- **새 최초 실패 (엄격 계약 유지):** source `ci/ch07_181_high_goal_precision_contract.py`는 high goal *예측* bin 중심 XY `<=0.005m`를 별도로 요구. Cycle10 선택기가 이전 넓은 `<=0.025m` high-native ROI만 고려했고, 실제 후보 목표 오차 **0.02046291m**여서 `real_arm_tracking_scoped_pass=False`가 됨. 오류 문자열 `G04B_181_HIGH_MOVEGROUP_ACTUAL_JOINT_TRACKING_FAILED`는 joint 오차가 작았음에도 **두 조건을 OR가 아닌 AND로 결합해서 나온 이름**임. 원본 Gazebo native rod high 이후 `[0.528893,0.242913,2.067270]`m, XY **0.0222650m**.
- 따라서 **목표 설계기와 정확도 계약 사이의 충돌**이 신규 RED. L2 후반 lower/release/settled ROI **NOT_RUN**. 기존 5mm 계약을 25mm로 수정하거나 실제 bin을 삭제·축소하면 안 된다. 물리 G04B **FAIL/BLOCKED**.
- 관측성 결함 별도 확인: CI Job summary에 약 1.9MB raw JSON 전체를 출력해 GitHub 1MB 제한 오류 `$GITHUB_STEP_SUMMARY upload aborted`. 원본 Artifact 원형 보존, 이후 SUMMARY는 10KB 이하 요약만 쓰고 전체 데이터는 Artifact 전용으로 유지.
- 보고서 후속 계획: **새 물리 L2 호출 전에** original real bin/link4/5mm/held offset/jaw 제약을 동시에 만족하는 high 목표의 기구학적 가능성을 오프라인으로 검토. 검증 가능한 목표가 없으면 보류하고 환경 또는 절차 아키텍처를 재검토. 반복 L2 금지.

**Cycle 10 CLOSED / G00~G04A ACCEPTED_NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
