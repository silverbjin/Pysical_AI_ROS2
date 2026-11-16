# G04B Cycle12 — 실제 solid bin 방향만 +0.35rad 변경한 새 시험 Fixture
_2026-11-16 / Issue #181 / active Draft PR #202 / 원본 G04B BLOCKED_

## RED
Cycle10 실제 L2 [#43788405858](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43788405858) Artifact #14191850785 ZIP SHA256 `665a6b73bfdd82771c6453c5a2b3daa4412ecff44b882bb65b8a5b398355e164`: 실제 rod 상승 0.11841m / hold drift 0.001399m, 고위치 실제 MoveGroup 성공, **기존 high 오차 20.46mm > strict 5mm**. Cycle11 L0는 기존 고정 bin yaw=0에서 새로운 충돌 없는 5mm 목표를 발견하지 못해 fail closed. 무의미한 Gazebo 재실행 금지.

## ONE real world fixture factor
기존 *진짜* 정적 bin 충돌 박스 [0.30,0.30,0.20]m와 중심 [0.55,0.25,1.63]m, 상단 1.73m, 동적 rod 50g, 모든 로봇 조인트·geometry·제어기·ROI·5mm 정밀도 유지. **물리 bin의 yaw만 0→0.35rad** 회전한다. 실제 물리 장애물 삭제/크기 축소/충돌 off 금지. 본 실험은 **원본 yaw=0 fixture 성공으로 소급 인정 불가**.

월드 SDF에서 단 한 필드 yaw만 바꾸는 불변식·기록을 적용한다. MoveIt에는 동일한 quaternion을 매핑하고 실제 FCL `plan_only` 후에만 새 Goal을 보낸다. 기록된 held native offset에서 오프라인 exact source 5DOF candidate는 high bin XY error <0.1mm, 실제 rotated bin vs link4 3D SAT clearance 약 4.3mm, jaw drift 약 0.203rad, tool-axis drift 약 0.080rad. 단지 계산 증거이며 실제 물리 성공 아님. 다른 held offset에서는 임계치 fail-closed.

## 변경/검증
- `ci/ch07_181_bin_yaw_single_factor.py`: world yaw 단일 필드 패치, 기존 전체 SDF 다른 필드 변경 금지
- `ci/ch07_181_rotated_bin_high_goal.py`: 실제 held source offset 적용, 결정론적 yaw/elbow Newton 교정, strict 5mm, original collision geometry SAT, jaw/tool safety
- `ci/ch07_181_bin_moveit_scene_contract.py`: 별도 C12 flag 에서만 원본 .35rad yaw 허용, 원래 yaw0 기본 계약 불변
- `ci/ch07_181_clearance_verified_high.py`: 원래 SAT 보존, optional actual rotated bin orientation
- `ci/ch07_77_g04b_actual_physics_witness.py` `physical_once.sh` 및 승인형 CI: C12 정확한 world와 FCL plan_only → 실제 high
- pure-Python L0 tests: 원본 bin shape/XY/top, yaw 복수변경 금지, original+rotated scene 구분, 실제 raw held offset+target 정밀도

L0/Python: PENDING. 실제 L2: NOT_RUN. 원본 증거를 감사한 후만 최종 판정.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**

## Cycle12 CLOSED — 실제 공개 Gazebo L2 원본 감사 (2026-11-16)

| 증거 | 확인 결과 |
|---|---|
| C12 PR HEAD | `8b7351ef68754997243b44b92ee1be089382f973` |
| 실제 CI checkout merge SHA | `ff315e8219fb4997b2a8e3446de28fce460389bd` |
| L0 | [#43791472642](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43791472642) SUCCESS; 일반 Book Lab [#43791472623](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43791472623) SUCCESS |
| 승인형 실제 Gazebo L2 | [#43791559566](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43791559566) **FAIL**; RUN NEVER ACCEPTED |
| 원본 Artifact | **#14192891264**, ZIP SHA256 `d549659106c7a42d46c77ce26d608405dc3d3e90d07523401b1f9b87a2849b9a` |
| 물리 50g rod 실제 상승 | **0.13986m**, 성공 |
| 실제 1.3초 hold drift | **0.00089981m**, 성공 |
| MoveIt 실제 장애물 | original solid box [0.30,0.30,0.20], centre [0.55,0.25,1.63], **실제 yaw=0.35rad 동일 quaternion** 등록 SUCCESS |
| 최초 실패 | `ValueError('C12_REAL_BIN_HIGH_SAFETY_OR_5MM_PREPLAN_UNPROVEN')` |
| 실제 high MoveGroup | **NOT_RUN**, fail-closed |
| 실제 lower/release/settled ROI | **NOT_RUN**, G04B 미완료 |

원본 `g04b_physical_receipt.json`의 held world rod=[0.4939,-0.006651,2.08032]m, 실제 rod-to-finger-centre offset=[-0.00580180,+0.00094007,+0.01868464]m. 이번 run의 실측 offset으로 C12 bounded 2변수 Newton seed를 다시 계산하면 새 high goal의 **정확한 XY 예측오차는 사실상 0m**이나, 원래 링크4 상자와 yaw=0.35 원래 크기 bin의 OBB SAT margin은 약 **0.000377m**, 고정 안전 여유 0.003m 미만이었다. 사전 검증이 올바르게 실제 Goal 전 종료. 고정 시험 fixture에 맞춘 L0의 양성 후보를 실제 입력 변화에 자동 외삽하면 안 된다는 실증이다.

보조 오프라인 그리드: 실제 held offset 조건으로 `q2,q4,qwrist` 후보와 XY 정렬된 `q1,q3`를 수백 개 탐색. 원래 5mm XY, jaw≤0.25rad, tool≤0.38rad, high z≥1.98m 하에서 조사한 후보의 최대 margin 약 **0.00086m**, 3mm margin 만족 후보 0개. 이는 **한정 탐색의 부정 결과이며 전역 기구학 불가능성의 증명이 아니다.** 새로운 실제 L2를 발사하기 전에 로봇 배치/기구학, 실제 grasp 후 오프셋 변화까지 포함한 안전한 기하학적 해를 먼저 찾아야 한다.

**최종 이 사이클의 판정: C12 CLOSED / G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.** 동일한 물리시험 무의미한 반복 금지. 원래 yaw0 fixture 역시 PASS로 소급 불가.
