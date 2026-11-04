# 13.7 BT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Single worker only. Steps use checkbox syntax.

**Goal:** 실제 동일 엔진 Nav2→fresh vision→pick을 BT로 지휘하고 모의 반응성 실습을 제공한다.
**Architecture:** 기존 실행기에 opt-in 단계 hook을 추가한다. 단일 worker가 ROS/engine을 소유하고 BT는 비동기 작업 snapshot만 읽는다. 10Hz tree와 기존 watchdog을 분리한다.
**Tech Stack:** ROS2 Jazzy, py_trees/py_trees_ros 2.6.0 후보, 기존 MuJoCo/MoveIt/native action.
**Spec:** SECTION_13_7_DESIGN_KO.md (2026-11-04 사용자 승인).

## Global Constraints

- f9957a55에서 새 branch/worktree, /home/jinho/ch13_reuse_13_7_build 별도 build.
- 단일 작업자; 기존 모델/정책·300ms 수명·물리 판정과 과거 증거 보존.
- BT update/terminate는 nonblocking; 늦은 수락도 소유 취소; terminal 후 자동 재실행 금지.
- 실제 운반/기립/충전 없음. 모의 출력은 profile=mock.
- build/test와 engine 동시 실행 금지. 실제 engine은 순차 실행.

## Review Focus

- pending goal 수락 중 INVALID: 늦은 수락 뒤 cancel 및 terminal 회수 (Task1).
- fresh vision을 복사한 후 만료: Pick은 live 원본을 재검사 (Task2).
- worker 예외·shutdown 중 pending: 실패 전달 및 join 확인 (Task1/2).
- low battery가 복구됨: abort latch로 재시작 방지 (Task1).
- 대체 build 경로가 기존 build의 부모/심볼릭 별칭: realpath 겹침 거절 (Task3).

### Task 1: 비동기 BT와 모의 반응성

**Files:** Ch13/ros2_ws/src/ch13_mission_orchestration/{package.xml,setup.py,setup.cfg,resource/*,ch13_mission_orchestration/{__init__,tasks,tree,mock}.py,test/test_bt.py}.
**Interfaces:** TaskPort.submit(name), snapshot(), cancel(reason); Mission(root, blackboard, terminal latch). Action operation tracker는 pending send와 result를 별개로 추적.

- [x] 실패 시험 작성: 단계별 single-submit/RUNNING→SUCCESS, 실패 전파, 정상/abort latch, 저전력 preempt, late acceptance cancel, worker 예외.
- [x] 시험 실행: missing package/module로 RED 확인.
- [x] 최소 tasks/tree/mock 구현. mock fetch/low_battery/fallen/not_found의 명시 profile와 tick 기록.
- [x] 같은 시험 GREEN 및 모의 CLI 사례 검증.
- [x] 선택 파일 commit.

### Task 2: 기존 실행기의 동일 엔진 hook

**Files:** Modify Ch13/scripts/reuse_13_5/run_navigation_probe.py; create Ch13/scripts/reuse_13_7/run_mission.py and installed ch13_mission_orchestration/session.py; modify existing planning.py only for the optional action client factory; test test_session.py.
**Interfaces:** opt-in orchestration.ready(node,until,snapshot), poll(), track_goal(sent), navigation_complete(payload), await_step(name,until), found(sample,clock_ns), cancel_requested(); absent hook preserves old behavior. TaskPort worker drives existing sole executor. Final names reflect the installed, byte-audited session adapter rather than a duplicated runner.

- [x] hook의 no-op 호환성·fresh capture·cancel/terminal 분리·worker 실패 전달 시험 RED.
- [x] navigation 시작 gate, 정착 완료 gate, 새 관측 gate와 pick gate를 작은 opt-in hook으로 연결. 기존 handoff/파지 절차 재사용.
- [x] ROS default executor 공유를 피하고 BT node와 robot node context/종료 소유권을 고정.
- [x] 시험 GREEN; 기존 navigation/manipulation 관련 suite 1회.
- [x] 선택 파일 commit.

### Task 3: 분리 build·동결·판정

**Files:** Ch13/scripts/reuse_13_7/{build.sh,env.sh,freeze_runtime.py,audit_install.py,run_case.sh,verify_mission.py}; dependencies/section_13_7_*; test/test_tools.py.
**Interfaces:** 7-package build, immutable source+assets freeze; verifier returns PASS only for actual lifecycle+BT+physical evidence; new UUID directory required.

- [x] build 겹침/실행 profile 혼동/만료 관측/취소 이후 pick/잔여 프로세스 거절 시험 RED.
- [x] 별도 BT dependency overlay 준비. sudo 비밀번호 없이 전역 설치가 안 되면 공식 deb를 새 build 전용 위치에 추출하고 버전·hash 기록.
- [x] build7 및 source/install/assets audit, 새 freeze 작성. 과거 freeze 수정 금지.
- [x] 부품 및 mock 검증 GREEN.
- [x] 선택 파일 commit.

### Task 4: 실제 인수·가이드·자체 검토

**Files:** Ch13/docs/LAB_13_7_BT_GUIDE_KO.md, SECTION_13_7_*REPORT_KO.md, evidence/section_13_7_bt/*.
**Interfaces:** 기존 verify_pick/verify_navigation의 측정 + 새 BT 순서/session verifier.

- [x] 가장 불확실한 실제 정상 BT pick 1회, 실패면 증거 보존하고 원인 조사. 취소1회 순차 실행.
- [x] 공통 hook 영향 최소 회귀, 필요 시 held_cancel. 판정기만 바뀐 경우 engine 반복 금지.
- [x] 다운로드/설치/build/환경/13.7.1~8별 명령·예상 출력·종료/실패 가이드 작성.
- [x] 모델 제외 archive/manifest 및 실행 시간/한계 기록. 전체 branch 자체 검토·최종 검증.
- [x] 선택 commit. 게시 범위가 별도 승인되지 않으면 로컬 branch로 보존하고 게시 상태를 정확히 보고.
