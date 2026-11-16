# G04B Cycle 09 — MoveIt real bin collision-free high elbow branch

- 날짜 2026-11-16 / Issue #181 / Draft #202 / main `9431fb535ce7a51416c19c4395fb2ba3fabdad40`.
- 출발 원본 Cycle08 L2 [#43780956237](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43780956237), Artifact #14188012578, ZIP SHA256 `8232ebeecd0c32bc7d3a1516218689f670043db8595277c50b1f8705cecb864e`.
- 상태: **Cycle09 개발·L0 대기 / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD**.

## RED: 고위치 자세 자체가 real bin과 충돌

기존 원본 실제 50g 원통 상승 0.14139m, 1.3초 hold drift 0.001077m. `/apply_planning_scene`에서 원래 static bin collision exact shape [0.30,0.30,0.20] at [0.55,0.25,1.63]m가 성공 적용됐다. 그 후 original high Goal `joint1≈0.419, joint2≈0.111, joint3≈+0.418, joint4≈1.179, wrist=0`를 실제 MoveIt OMPL이 충돌 판정: `g04b_existing_gazebo_bin_collision` ↔ `link4`. RRTConnect `Unable to sample any valid states for goal tree`; high Goal ABORTED, planned_points=0. **실제 장애물을 빼서 인위적으로 계획 성공시키면 안 된다.**

## 한 가지 반증 가능한 대안

**팔꿈치 대체 IK branch만 변경**한다. 기존 2R position IK `joint3=+acos(c)` 대신 `joint3=-acos(c)`로 같은 높은 wrist 위치를 맞추고, `joint2`를 동시 보정한다. 실제 held rod offset을 써서 bin XY [0.55,0.25]를 ±3mm로 맞추고, 원래 world jaw normal을 기존 `high_carry_jaw_compensation`으로 보존한다. 다른 robot/SDF/bin collision/MoveIt tolerance/물리 solver/ROS Actuator/FJT 항목은 불변.

기존 원본 Cycle08 frozen hold sample의 순수 계산 예시: 원래 목표 wrist [0.511946,0.228099,1.96]m에서 대체 분기의 고위치 wrist ≈[0.53212,0.23709,1.96]m; 예측 `joint2≈0.639rad`, `joint3≈-0.351rad`, bin XY≈0. 실제 목표 정확도·collision-free 판정은 새 공식 MoveIt 계획과 Gazebo 관절 feedback으로 독립 검증한다.

## CODE / Test / Gate

- `ci/ch07_181_collision_free_high_branch.py`: 대체 팔꿈치 분기 8회 순수 수치 보정, 진짜 held offset·0.003m XY·joint limits·world jaw angle 검사, 결과는 KINEMATIC 후보일 뿐.
- `ci/tests/test_ch07_181_collision_free_high_branch.py`: 실제 Cycle08의 held 5DOF 값과 rod offset으로 양성 단위시험, NaN·범위 초과 입력 거절.
- `ci/ch07_77_g04b_actual_physics_witness.py`: `CH07_181_C09_NEGATIVE_ELBOW_TRIAL=YES`일 때만 alternate goal을 계산하고 **real MoveGroup `plan_only=True`가 실제 collision-aware path를 승인해야 실제 high Goal 수행**.
- `ci/ch07_77_g04b_physical_once.sh`: 1회 CI 시험용 flag만 활성화. 실패하면 다시 시도하지 않고 flag 원복·원본 수치 보존.
- `.github/workflows/book-ch07-77-g04b-real-grasp.yml`: 자동 PR L0, 물리 L2는 새 `g04b-physics-once` 라벨 1회.

**기존 수용 조건 유지:** native bilateral contact, lift>=0.05m, hold1.3s, high custody, lower, real release, settled ROI와 모든 actual joints. Plan-only GREEN은 물리 G04B PASS 아님.

## 실험 결과 / 교육용 판정

- L0: PENDING
- L2: NOT_RUN
- Artifact SHA256: NOT_RUN
- 변경 요인: **대체 high elbow 목표의 joint configuration 한 가지**
- G04B: BLOCKED

**교육용 핵심:** MotionPlanner가 collision으로 거부하면 장면을 숨기거나 관절 허용오차를 늘리는 대신, 기구학적으로 가능한 **다른 관절 branch**를 검토한다. 그 branch가 안전한지는 알고리즘의 수치 정확도 → MoveIt 충돌 계획 → 실제 Gazebo 접촉·운반·배치의 순서로 입증해야 한다.
