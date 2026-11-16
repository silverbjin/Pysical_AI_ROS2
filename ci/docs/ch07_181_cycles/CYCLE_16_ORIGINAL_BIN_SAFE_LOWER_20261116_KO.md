# G04B Cycle16 — 고위치 파지 성공 이후 원본 solid bin 충돌 안전 하강

_2026-11-16 / Issue #181 / 단일 활성 Draft PR #202 / 적용 표준 BOOK_ROS2_DEV_DEBUG_CI_STD_V1_

## RED — 실제 Gazebo 원본의 최초 불일치

- [Cycle15 실제 CI #43796136009](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43796136009) FAIL, Artifact **#14194442014**, ZIP SHA256 `ed34ede877805df1b4c134648ba88d005a1894c1c99cd54b8d3926499dee1f7e` 원본 다운로드·독립 SHA256 검증 완료.
- PR HEAD `8eaa12518333f23d2eb26b0d6e68a87c27a22c19`; 실제 PR checkout merge SHA `72f5e9834077b74deae0b22177412c81f933a217`; 동일 소스라고 잘못 표시 금지.
- 50g 실제 rod 상승 **0.138570m**, 1.3초 hold drift **0.001264566m**, 양측 실제 FJT/접촉 확보. 고위치 MoveIt 실제 collision-aware 계획·실행 29점 **SUCCEEDED**. 원본 rod high XY **0.00414482m**, world custody drift **0.00229196m**. 이 단계까지 실제 고위치 성공.
- 최초 실패: `lower_into_bin` 실제 MoveIt이 목표 자체를 **거부**: `ABORTED`, error `99999`, planned_points=0; MoveGroup 로그의 `g04b_existing_gazebo_bin_collision` vs `link4` contact. 하강 관절 Goal 명령은 전송되지 않았으므로 `joint3`가 멈춘 게 근본원인이 아님. 본문 역사적 C06 lower 목표 `q=[.4582367,-.2940863,1.05,1.4466502,-.2186564]`의 원래 yaw=.35 고체 bin vs link4 3D SAT margin 약 **-0.03638m**, 물리적 교차 증명.
- 실제 lower 물체 z/배치/해제 **NOT_RUN**. L2 실패를 원통 안착 PASS로 승격하면 안 된다.

## 가설 하나 / 변경 요인 하나

**오직 하강 단계의 5DOF 목표 관절 자세만 변경**한다. Cycle15에서 성공한 파지·상승·고위치 29점 운반 코드와 원래 실제 동적 50g rod, fixed test-only robot SDF, yaw=.35rad의 정적 solid bin 크기/위치/충돌 물리, MoveIt/FJT 속도·허용오차, 정확한 5mm high 계약, native bilateral contact, lower/pre_release/settled ROI는 불변.

## 구현/반증

1. `ci/ch07_181_original_bin_safe_lower.py`: C15 실제 high 5DOF + 그 세션에서 측정한 real held offset 기반, q3≤C06의 검증된 1.05rad, 원래 3D OBB SAT와 9점 보간의 링크4 충돌 미교차, 원통 중심 기존 `XY≤0.06m`보다 보수적인 `XY≤0.055m`, 기존 `z≤1.92m`보다 보수적인 `z≤1.915m`, jaw .25rad→내부 preview .245, tool .38rad→내부 preview .375, margin .003→내부 preview .0045; 원래 판정기를 바꾸지 않는다. 후보 없으면 `C16_NO_COLLISION_SAFE_REAL_BIN_LOWER_GOAL`.
2. `ci/tests/test_ch07_181_original_bin_safe_lower.py`: 직전 원본 충돌 하강 자세 부정, 실측 high/offset 양성 후보, 원본 bin 변경/미검증 scene·불완전 JointState·가짜 파지 거부.
3. 실제 witness는 `CH07_181_C16_COLLISION_SAFE_LOWER=YES`일 때만 새 goal을 사용하고 **독립 실제 MoveIt `plan_only`가 성공하기 전 하강 actual Goal 금지**. 이후 실제 Goal 및 모든 native 실물체/접촉/ROI 게이트 유지.
4. 오프라인 독립 source FK+SAT 검사에서 한 원본 C15 실측 후보의 예측 rod `[0.49908,0.24380,1.91254]`m, XY≈0.05129m, link4 vs original solid bin SAT≈+0.005806m, world jaw≈0.232rad, tool≈0.262rad, 9점 보간 미교차. **기구학적 후보일 뿐 공식 MoveIt path나 실제 물리 완료가 아니다.**

## 개발·디버깅·증거 기록

- L0: 새 관련 단위시험/syntax/원본 해시만 공개 CI 실행; 성공 전 L2 금지. Run ID는 후속 결과 커밋.
- L2: 이전 승인형 라벨을 제거한 후 새 `g04b-physics-once` 라벨 이벤트 **1회**, 원본 Artifact 별도 감사.
- 종료: 하강 성공 이후에도 실제 pre-release native bilateral recent contacts, 원통 이동·배치 해제, settled XY ≤.09m / 높이 |z-1.77m|≤.055m 등을 전부 확인해야 물리 PASS.
- 교육 회고: MotionPlanner가 충돌 목표를 안전 거부한 시점을 **컨트롤러 동작 실패**로 오분류하지 않는다. 기존 원본 물리 obstacle과 장비 제약을 바꾸지 않고 실측 high pose 기반으로 하강 목표만 새로 설계한다.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY.**
