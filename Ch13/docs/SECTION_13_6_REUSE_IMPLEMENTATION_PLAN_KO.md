# 13.6 Manipulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. 단일 작업자로 실행한다. 사용자는 2026-11-03 설계 및 진행을 승인했다.

**Goal:** 같은 Go2+Piper engine에서 접근→MoveIt 계획→물리 파지→10cm lift를 실제 상태와 수명 증거로 확인한다.

**Architecture:** 작은 opt-in platform extension에 session lease와 표준 trajectory/gripper action을 둔다. native PD/보행 loop/관측 소유권은 재사용하고 계획·비전·mission은 새 패키지에 둔다.

**Tech Stack:** Jazzy, MoveItPy/MoveIt2 2.12.4, TRAC-IK 2.0.2, MuJoCo3.13.0, CPU ONNX, Python3.12.

**Spec:** [승인 설계](SECTION_13_6_REUSE_DESIGN_KO.md), [M0](SECTION_13_6_REUSE_M0_REPORT_KO.md).

## Global Constraints

- 단일 작업자. sources/, 다른 장, 기존 evidence/freeze/외부 원본/R5 build를 변경하지 않는다.
- physics2ms/policy50simHz/원본 cap/native PD 유지, 원본 capture/receipt/GID/age300ms/과거TF100ms 보존.
- 새13.6 branch/build/evidence/freeze. 엔진은 순차 실행, 실행 중 build/pytest 병행 금지.
- fake joint_states, torso 고정/teleport, 물리 weld, 정책 kill로 성공 처리 금지.
- 실패 보존. 같은 실패 두 최소 수정 후 구조 검토. 필요한 외부 변경은 실제 내용을 밝힌다.

## Review Focus

1. 반복 heartbeat가 오래된 capture를 살리지 않는다 — Task1 replay/expiry 시험.
2. cancel ACK 뒤 실제 움직임과 terminal을 구분한다 — Task2 cancel/hold 시험.
3. 동적 freejoint 추가가 robot joint indexing/TF를 망가뜨리지 않는다 — Task4 모델/관측 시험.
4. planning scene revision과 실제 state가 바뀐 뒤 옛 궤적을 실행하지 않는다 — Task3 stale plan 시험.
5. 실패 실행도 child/renderer/lock을 회수한다 — Task5 실패 회수 시험.

### Task 1: M1 live handoff

**Files:** 새 `ch13_manipulation_reuse/{lease.py,engine_extension.py}`, package.xml/setup.py, `test/test_lease.py`; 수정 `platform_adapter.py`, `navigation.launch.py`, `run_navigation_probe.py`, native `ingress.cpp`; 새 `reuse_13_6/{build.sh,env.sh,run_handoff.py,audit_install.py}`.

**Interfaces:** Lease(session).observe(observation, owner, receipt); .heartbeat(payload, owner, receipt); .evaluate(clock_ns, wall, settled, supported, goal_status, actual_pose, navigation_idle)→phase/fault. extension의 status/session을 platform/status에 추가. 기존 main(argv=None,handoff=None) callback은 살아 있는 node/until/call/snapshot을 받는다. 기본 실행 행동 불변.

- [x] RED: test_lease.py에서 정착 전 거절, 과거 session, owner 교체, 반복 stamp/seq, capture300ms/TF100ms 만료, 정상 READY→회수, 새로운 goal의 회수를 검증. `pytest .../test_lease.py -q`가 import 실패해야 한다.
- [x] GREEN: lease와 opt-in extension/ingress·callback 구현. 새 build는 기존3개+새 패키지를 선택하고 R5 경로를 거절. pytest가 모두 통과해야 한다.
- [x] 실제 build/audit 뒤 vision 접근→같은 engine에서 2wall초 READY 유지→명시 회수→정상 종료. 이전 session/만료 injection 별도 사례. summary와 상태/lease 이벤트·join/잔여검사 저장.
- [x] M1 보고서와 선택 commit.

### Task 2: M2 actual arm/gripper boundary

**Files:** 새 `trajectory.py`, `action_bridge.py`, `test/test_trajectory.py`, `reuse_13_6/run_arm_probe.py`, contract JSON. extension에 단일 command slot 연결.

**Interfaces:** validate_trajectory(joint_names, points, measured_q, limits)→immutable trajectory; sample(sim_s)→q,qd,qdd; cancel(sim_s)→bounded brake/hold. FollowJointTrajectory joint1~6와 GripperCommand joint7만 제공. engine actual feedback.

- [x] RED: 순서/NaN/시간역행/중복관절/한계/초기불연속/속도·가속도 초과/종료속도 및 cancel 연속성/lease 만료 시험. 실패 원인 확인.
- [x] GREEN: 검증·보간·sim-time 실행·feedback·취소/hold, 실제 관절/힘/추종/지지 watchdog. joint1 parameter와 상호배타. gripper equality/cap 유지. 전체 suite PASS.
- [x] 실행 전 작은6축0.02rad·속도0.05rad/s·가속도0.1rad/s² 계약 동결. 실제 추종·취소·heartbeat 손실·중복 소유자·gripper 개폐를 순차 시험. engine 측정으로 성공 판정.
- [x] M2 보고서와 선택 commit. 단순 관절 시험을 파지 성공으로 세지 않는다.

### Task 3: M3 accurate planning and execution

**Files:** 새 `ch13_piper_moveit_config`의 model generator/URDF/SRDF/config/launch, `planning.py`, `test/test_model.py`, `test/test_planning_contract.py`, `reuse_13_6/run_moveit_probe.py`.

**Interfaces:** generate_model(compiled_mujoco)→URDF/SRDF+hash manifest; assert_plan_current(scene_revision,start_state,capture,clock)→admission. Python wrapper는 OMPL plan과 GetCartesianPath를 사용, 같은 action으로 실행.

- [x] RED: 통합 모델 한계/FK/TCP 및 conservative collision 포함, q8 mimic, TF/joint owner 중복 없음, stale scene/state/capture와 partial Cartesian 거절 시험.
- [x] GREEN: 모델/설정/장면 sync와 actual execution. FK 위치≤1mm/회전≤1mrad 대조, 팔6축 group+gripper mimic, actual base virtual joint. 설치 API만 사용.
- [x] MoveIt 실제 pose 도달/불가/충돌거절/Cartesian 전체 경로/취소 시험. scaling≤0.1, 시간·joint jump·실제 최종 pose 검증. 성공/실패 분리 저장.
- [x] M3 보고서와 선택 commit.

### Task 4: M4 physical picking

**Files:** 새 `pick_scene.py`, `cylinder_vision.py`, `pick_mission.py`, 해당 tests, `reuse_13_6/run_pick.py`, scene/acceptance 계약 JSON. 공유 센서의 opt-in camera hook.

**Interfaces:** fit_cylinder(rgb,depth,K,T_capture,radius,height)→center/axis/residual/provenance; pick sequence는 M1 lease/M2 actions/M3 planner를 사용. oracle qpos는 evidence 평가 전용.

- [x] RED: upright 실제 depth 표면 fit·가림/점부족·만료·joint indexing·정상 target-support와 금지 robot-support 접촉 구분 시험.
- [x] GREEN: 별도0.02kg/radius0.02m/height0.08m/friction0.8 cylinder 장면. 공개 치수+RGB-D fit, 허용 finger-target contact만 단계 한정. 전체 tests PASS.
- [x] 시험 전 물체/받침 pose·TCP/fit/jump 한계 고정. open→pregrasp0.10~0.15m→직선접근→close/양finger접촉→직선lift0.10m→hold2sim초. 실제상승≥0.09m·상대변화≤0.02m·낙하없음 확인. 실패도 기록.
- [x] M4 보고서와 선택 commit. 힘/물체를 조용히 바꾸지 않는다.

### Task 5: M5 freeze, acceptance, guide, publication

**Files:** `section_13_6_reuse.lock.json`, freeze/install audit/verification tools, `LAB_13_6_REUSE_GUIDE_KO.md`, 최종 보고서/evidence manifests.

**Interfaces:** freeze는 이번 source/install/model/policy/수치 해시만 기준으로 한다. verifier는 실제 trajectory/contact/물체 변위/lifecycle를 독립 계산한다.

- [ ] RED/GREEN: 판정기의 실패 evidence(불완전lift/실제 terminal 없음/잔여PID/가짜상태) 거절 시험.
- [ ] 최종 수치/source/install/model/policy 동결 후 필수 각1회 matrix: pick/불가·충돌/취소/입력·관측손실/중복/정상정착·종료. 공유변경 영향의13.5 실제 접근·취소·정지 회귀.
- [ ] 다운로드→설치 의존성→build→환경→소절명령→성공/실패/종료 판독 가이드. 미검증/실패·교육profile 제한 명시.
- [ ] 단일 작업자 별도 전체 diff 검토 및 필요한 수정 검증. 선택 commit/non-force push·remote SHA 대조. main/PR 불필요.
