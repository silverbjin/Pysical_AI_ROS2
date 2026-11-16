# G04B Cycle15 — 실제 C14 held-time 입력에 맞춘 수치 정밀도 보완

- 날짜: 2026-11-16 / Issue #181 / Draft PR #202.
- 원본 RED: [C14 실제 Gazebo #43794623418](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43794623418), Artifact **#14193344668**, ZIP sha256 **3928683bc9e88ab1599b1831ca20145dfb6bd1cea7df55eff9286ed19e51a675** (독립 재다운로드·SHA256 재검증).
- 실제 50g rod lift **0.139140m**, 1.3s hold drift **0.000641627m**. held-time 실제 q=[-0.02480023,-0.06022640,+0.56993304,+1.56211117,+0.02329851]rad, 실제 rod-to-finger offset=[-0.00641171,+0.00157323,+0.02020364]m. 첫 실패 `C13_NO_SAFE_HIGH_GOAL_FOR_ACTUAL_HELD_OFFSET`, 실제 high plan_only/Goal, lower/release NOT_RUN.
- 가설: 현재 고정 3mm/6mm target posture 격자가 엄격한 3D SAT margin ≥3mm, ideal bin XY ≤5mm, world jaw drift ≤.25rad의 좁은 교차 영역을 놓쳤다. 기존 동일 원본 q와 offset의 독립 연속 기구학 계산에서는 SAT≈3.6mm, XY≈4.2mm, jaw≈.198rad인 후보 존재. 계산은 FCL/물리 PASS가 아니다.
- **오직 한 가지 코드 변경:** 기존 빠른 q2/q4/wrist 후보 탐색은 유지하고, 후보가 0개일 때만 실제 held offset의 좁은 1mm 간격 q1/q3 보정 근방을 유한하게 재검사. SciPy/무작위/새 물리 엔진 없음.
- `ci/ch07_181_rotated_bin_high_goal.py`: `local_refinement_used` 영수증 필드. `ci/tests/test_ch07_181_rotated_bin_high_goal.py`: C14의 **동일 held-time q/offset 원본** 신규 회귀시험, 기존 C12/C13 tests/불법 bin shape/scene/NaN guard 보존.
- 변경 금지: 동적 rod 50g, 실제 Gazebo bin/URDF/물리 solver/friction, 원본 static bin yaw=.35/shape/pose, MoveGroup/FJT tolerances, native contacts, lift/hold/high/lower/release/settled ROI. **L0 계산과 FCL plan_only는 실제 G04B PASS가 아니다.**
- L0: CI Run ID 후속 갱신 / L2: 명시적 `g04b-physics-once` 1회 후 원본 감사. 아직 G04B BLOCKED.

**교육적 핵심:** `NO_SAFE_HIGH_GOAL`은 해의 부재가 아닌 **탐색기 해상도의 부재**일 수도 있다. 같은 시각의 실제 JointState와 원통 offset을 회귀 fixture로 고정해 먼저 반증하고, 안전 판정기를 완화하지 않는다.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
