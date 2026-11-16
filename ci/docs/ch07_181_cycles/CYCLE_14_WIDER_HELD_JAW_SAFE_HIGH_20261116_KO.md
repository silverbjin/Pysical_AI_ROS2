# G04B Cycle14 — 실제 held jaw 방향에 따른 고위치 목표의 탐색 범위 교정
_2026-11-16 / Issue #181 / 활성 Draft #202_

## 원본 실패 고정 (RED)

- 직전 L2 [#43793586874](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43793586874), Artifact #14193288185, 원본 ZIP sha256 `53c6c93d8ddba9de6f698296d236dc40d163c1338ee1fdf09b3fcc27c29cf89e` (실제 독립 다운로드·SHA256 재검증 완료).
- 원본 동적 50g rod 실상승 **0.152610m**, 1.3초 hold drift **0.00107990m**, 실측 finger close/ native contact 기록 존재.
- 원본 관찰 offset **[-0.0011352623,+0.0011248490,+0.0168798705]m**; 가장 최근 저장된 lift final q4 ≈ **1.548rad**. 이전 고정 seed 기준선에 비해 grasp jaw 세계 방향이 달라져 이전 q4≥1.42 근방에서는 전항목 통과할 후보가 없음. 실제 held 시점 관절을 별도 기록하지 않았으므로 lift snapshot과 **동일시하지 않음**.
- 처음 실패: `C13_NO_SAFE_HIGH_GOAL_FOR_ACTUAL_HELD_OFFSET`. 실제 high, lower, release, settled **NOT_RUN**.

## 원인 가설과 변경 한 요인

로봇·bin collision/크기/중심/yaw=.35rad·동적 rod/FJT/MoveIt/속도/solver/접촉/3mm 여유/5mm 정확도/0.25rad jaw/0.38rad tool 허용치는 **전혀 변경하지 않는다**. 수정은 **high target 근방 joint4/wrist 후보 분포만** 확장: `joint4 1.250..1.500rad`, `joint_wrist -0.255..-0.075rad`, finite bounded deterministic grid. 각 시도는 원래 3D OBB SAT+strict 5mm+실제 held offset+world jaw/tool 안전 조건 통과 후 최적 headroom만 선택; 후보 없음이면 원래대로 Goal 전 FAIL.

## 선택적 TDD 및 원본 비교

- 실제 Cycle13 held offset + 원본 lift stage arm JointState를 서로 다른 시각이라는 주석과 함께 추가 실패 회귀 입력으로 사용. 이전 샘플 2종과 함께 원래 엄격한 gate 통과 여부를 검증.
- witness에 **실제 held 시점의** `cycle14_actual_held_arm_jointstate_pre_high`만 읽기 전용으로 추가, 새로운 Goal 명령/ROS/물리 변경 0.
- MoveIt FCL `plan_only` 성공 확인 전 actual high Goal 송신 금지. 이후 native bilateral contact·lift·hold·high·lower·release·settled ROI는 각각 별도 검증.

## 실행 기록

- L0: PENDING (공개 CI 원본 Run ID 기입 예정)
- L2: NOT_RUN (L0 승인 후 새 label 이벤트 1회만)
- 교육 포인트: 실패한 관절 상태 자체를 L0 참고 fixture에 동결하되, `lift`와 `held`의 시각을 혼동하면 반례 검증이 과장된다. 관절 목표는 정확한 held-time 입력으로 계산해야 한다.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
