# G04B Cycle13 — 실제 held offset에 적응하는 최소 고위치 목표 선택기
_2026-11-16 / Issue #181 / Draft PR #202 / 승인 표준 BOOK_ROS2_DEV_DEBUG_CI_STD_V1_

## RED — 실제 원본 증거

Cycle12 승인형 공개 Gazebo [Run #43791559566](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43791559566) / Artifact **#14192891264** / ZIP SHA256 `d549659106c7a42d46c77ce26d608405dc3d3e90d07523401b1f9b87a2849b9a`은 실제 50g rod **0.13986m 상승**, 1.3s hold drift **0.00089981m**, 실제 solid bin yaw=.35 PlanningScene SUCCESS를 보였지만, 최초 C12 high `plan_only` 전 기하 가드 `C12_REAL_BIN_HIGH_SAFETY_OR_5MM_PREPLAN_UNPROVEN`으로 종료했다. 실측 held rod-to-gripper offset `[-0.00580180,+0.00094007,+0.01868464]m`을 반영한 기존 **고정 seed**의 충돌 SAT 여유는 **0.000377m**, 요구 0.003m 미만. high/lower/release NOT_RUN. 이 원본을 절대로 PASS로 승격하지 않는다.

## 실제 원인과 단일 가설

C12 기구학 후보는 이전 한 개의 held-offset sample에 맞춰 q2/q4/qwrist를 고정하고 q1/q3만 보정했다. Gazebo가 실제로 형성한 수 mm 다른 파지 오프셋에서는 목표가 `link4`↔bin 충돌 여유를 잃었다. **단일 수정 요인: 고위치 목표의 관절 자세 선택기만 실측 held offset에 적응**시킨다. 테스트 bin의 **실제** solid box [0.30,.30,.20], 중심 [.55,.25,1.63], yaw=.35rad, robot/rod, 물리 solver, 동일 MoveGroup/FJT tolerances, native collision/contact/ROI/5mm 허용치를 모두 보존한다.

## 최소 구현

- `ci/ch07_181_rotated_bin_high_goal.py`: 원본 5DOF FK와 3D OBB SAT, real held offset, jaw/tool 방향 검사. 제한된 결정론적 q2/q4/wrist 근방 자세군만 생성, 각 후보의 q1/q3는 원래 exact FK와 2×2 Jacobian으로 중심 XY를 보정. 5mm XY·분리 3mm·jaw .25rad·tool .38rad·high z≥1.98m를 **동시에** 만족하고 세 독립 여유를 균형 있게 유지하는 후보 한 개만 반환. 실패하면 안전한 high Goal을 만들지 않고 `C13_NO_SAFE_HIGH_GOAL_FOR_ACTUAL_HELD_OFFSET`으로 STOP.
- `ci/tests/test_ch07_181_rotated_bin_high_goal.py`: 이전 L0 reference offset과 직전 L2에서 관찰된 **새 실제 offset**을 별도 단위 사례로 검사. 잘못된 bin shape/pose/yaw/scene, NaN, 파지 이탈 거부.
- 기존 승인형 L2 witness의 **MoveIt plan_only 성공 후 실제 Goal** 게이트는 수정하지 않음. 이 후보를 통과시켜도 Gazebo actual contact/lift/high/lower/release/settled ROI 미검증.

## 독립 오프라인 실험 — 설계 단계

기존 exact source 기구학의 별도 Python 수치계산(ROS/Gazebo Goal 아님)에서 직전 L2 관찰 offset을 대입하여 SAT clearance 약 **4.43mm**, high rod-bin XY 약 **3.26mm**, world jaw 약 **0.241rad**, tool 약 **0.084rad**의 후보를 발견하였다. 이는 **기하학적 후보만**이며 진짜 MoveIt FCL 경로, 실제 동역학, 배치 성공의 증거가 아니다.

## TDD / CI / 판정

- L0: 단위 코드와 함께 커밋 → 자동 공개 CI Run ID를 확인한 뒤 이 보고서에 추가.
- L2: L0 성공 및 단일 실측 가설 명시 후 새 `g04b-physics-once` 라벨 이벤트 **1회만**.
- 실패하면 원본 Artifact의 **첫 실패**만 독립 감사하여 동일한 목표 재시도 금지. 성공하더라도 최종 native bilateral contact, lift/hold/carry, lower/release, settled ROI를 모두 감사하기 전에는 물리 인수 아님.

**G00~G04A ACCEPTED_NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## Cycle13 L0→실제 Gazebo 원본 결과 — CLOSED / G04B BLOCKED

- 소스 PR HEAD `57cf1458ccacda25482562bbb79153fd2de4c411`; 실제 Actions merge checkout `ea9b5d7937b59e777317452b638ff88e17b89c4c` (`receipt.source_sha`).
- [L0 #43793516668](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43793516668) **SUCCESS**, 일반 문서 [#43793516819](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43793516819) **SUCCESS**, physical SKIPPED.
- 승인형 실제 [L2 #43793586874](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43793586874) **FAIL**. 원본 Artifact **#14193288185**, ZIP SHA256 `53c6c93d8ddba9de6f698296d236dc40d163c1338ee1fdf09b3fcc27c29cf89e`. 독립 ZIP 원본 다운로드·해시/receipt/로그 감사 완료.
- 실재 50g rod 상승 **0.152610m**; 1.3s hold drift **0.00107990m**. FJT real bilateral closed fingers 약 [0.011478,0.011500]m, native finger1/finger2 접촉 쌍 진단 존재. 정적 실제 bin yaw=.35 quaternion 동일, PlanningScene 등록 성공.
- 최신 **실제 held offset**=[-0.0011352623,+0.0011248490,+0.0168798705]m. 최근 독립 lift arm JointState의 q4는 약 **1.548rad** (이 값은 이후 held 시각과 동일하다는 뜻은 아님). 기존 C13 근방 q4=[1.420,1.480] 및 wrist=[-.215,-.165] 목표는 **안전 후보 없음**.
- **최초 실패** `C13_NO_SAFE_HIGH_GOAL_FOR_ACTUAL_HELD_OFFSET`. MoveIt high plan_only, actual high Goal, lower/release/settled **NOT_RUN**. 이것은 **실패를 안전하게 걸러낸 증거**이지 물리 완료가 아니다.
- 다음 Cycle14 한 요인: 실제 파지 후 jaw 방향 변화를 수용하도록 고위치 `joint4`/wrist 근방 후보 범위만 확대하고 source 수용 기준/물리 solver/bin/robot 그대로 유지. 실제 held joint orientation을 함께 receipt에 저장하여 이전/현재 원본을 혼동하지 않는다. **반복 물리시험은 C14 L0 통과 이후 한 번만 허가.**
