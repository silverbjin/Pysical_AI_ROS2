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
