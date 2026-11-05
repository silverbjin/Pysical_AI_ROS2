# 13.7 M0: 원고·기준·실행 경계 조사

2026-11-04 KST. 단일 작업자. 13.7 패키지 구현·설치·engine 실행 전 조사다.

## 확인 결과

- 실제 인계 파일 Ch13/docs/HANDOFF_SECTION_13_7_2026_11_04_KO.md와 첨부 원고 전체를 읽었다. 인계 시점과 달리 원고가 이번 요청에 첨부돼 있다.
- 사용자가 실제 BT 이동→관측→파지 통합 및 확장 동작 모의 실습을 선택했다.
- 적용 프로젝트 AGENTS.md: sources 읽기 전용. 추가 AGENTS 파일은 rg 검색에서 확인되지 않았다. 기존 사용자 파일과 Ch01~12는 변경하지 않았다.
- 원래 worktree: work/Pysical_AI_ROS2_reuse, branch feat/ch13-section-13-6-manipulation, HEAD f9957a5535ff56b321db334a241cd689b4f3e583. 최초 status는 인계 문서 하나 untracked. git remote는 https://github.com/silverbjin/Pysical_AI_ROS2.git.
- GitHub 연결 도구 get_pr_info로 PR #115를 재조회했다. closed/merged=true, head f9957a55, merge commit 956919aef2a9732cc7be4c311fa2789f17a43945, merged_at 2026-11-03T18:55:15Z(2026-11-04 03:55:15 KST). 인계 시점의 open 기록은 역사로 보존한다. 현재 main의 최신 head 또는 remote branch SHA를 git ls-remote로 재조회한 것은 아니다.
- 기존 git worktree list는 과거13.5와13.6 두 경로다. 후보 work/Pysical_AI_ROS2_13_7과 feat/ch13-section-13-7은 조회 시 없음. 새 worktree/branch는 아직 만들지 않았다.

## 환경과 현재 소유 상태

초기 일반 권한의 Windows CIM/WSL 조회는 접근 거부됐다. 필요한 WSL 조회를 승격으로 다시 실행해 성공했다. Windows 전체 process inventory는 확보하지 못했으며 WSL 결과를 Windows 전체 무실행 보증으로 확대하지 않는다.

WSL Ubuntu-24.04의 ps 전체 목록에 ch13 engine/MoveIt/실행 스택은 없었다. ROS_DOMAIN_ID=136의 기존 ros2 daemon PID6660은 관찰했으며 종료하거나 변경하지 않았다. lslocks에서도 ch13 engine 소유 잠금은 관찰되지 않았다.

기존 공식 inspect_r2_residuals.py를 실행했다. [pre_residual.json](pre_residual.json)에 owned_stack_matches=[], engine_lock_free=true, result=PASS를 저장했다. 이 도구는 특정 모듈 패턴과 실제 flock 획득 가능성을 검사한다. 모든 가능한 다른 프로그램을 포괄하는 검사라고 주장하지 않는다. 엔진 실행 직전 재확인해야 한다.

기존 /home/jinho/ch13_reuse_iit_d010212_venv, /home/jinho/ch13_reuse_13_6_build, /home/jinho/ch13_reuse_13_6_guide_validation_v13_20261104 경로 존재를 확인했다.

기존 env.sh로 freeze_runtime.py verify를 실행해 result=PASS, revision=13_6_navigation_formal_acceptance_v14, source_files=251, assets=94, manifest SHA256=9605c2c9d3b411b3f89f3c8b533f110042aa48d8cff5331983a3f58dcea6c000을 확인했다. source/외부 자산 검사이며 별도의 전체 설치 ELF 감사나 새 물리 시험 결과는 아니다.

dpkg-query에서 ros-jazzy-py-trees/ros-jazzy-py-trees-ros는 미설치였고 시스템 Python find_spec도 둘 다 None이었다. 이번 조사에서는 apt/pip 설치나 시스템 설정 변경을 수행하지 않았다.

## 읽은 실행 경계

- run_navigation_probe.main은 startup/admission, Nav2 send/get_result, zero/정착, fresh 관측과 workspace 검사 뒤 opt-in handoff를 호출한다. planner를 살아 있는 engine clock에서 회수하고 shutdown/join/잔여를 검사한다.
- run_handoff.handoff는 50ms heartbeat로 session/goal/seq/원본 capture를 전송한다. work 완료 후 REVOKED를 기다리고 timer/publisher/subscription을 파괴한다.
- run_pick.work는 기존 Planner와 GripperCommand를 사용해 장면→양 finger 접촉→lift→fresh vision 보정/정착→hold→POST_SETTLE을 수행한다. finally에서 planner/gripper를 회수한다. 현재는 blocking until 기반이며 BT update에 그대로 호출할 수 없다.
- Lease는 300ms 원본 관측/heartbeat와 session·owner·goal·정착/지지를 검사한다. NEW_NAV_GOAL은 fault, REVOKED는 terminal이다. 원본 capture 수명을 갱신하지 않는다.
- 13.6 build.sh는6개 패키지만 선택하며 R2/R5 경로만 보호한다. 13.7 별도 build 도구가 필요하다. 기존 freeze/audit를 수정하여13.7 통과로 만들지 않는다.

## 원고와 연결할 차이

원고 Nav2Client는 get_result_async 및 terminate 취소가 생략된 개념 코드다. accepted와 실제 terminal을 분리해야 한다. low battery Condition 단독 FAILURE는 Selector에서 다음 가지 실행을 허용하므로 저전력→중단/충전 가지로 고친다. 정적 render_dot_tree는 자동 실시간 상태 뷰가 아니다. 원고의 운반·기립·YOLO는 현재 실제 검증 범위와 다르며 선택한 모의/실제 범위에 맞춰 안내한다.

공식 py_trees/py_trees_ros 문서를 조회해 Selector 우선순위 전환의 INVALID 처리와 BehaviourTree의 node/timer API가 버전별로 다름을 확인했다. 설치 버전은 아직 확인할 수 없으므로 구현 전 실제 signature를 확인해야 한다.

## 산출물과 남은 일

[상세 설계안](SECTION_13_7_DESIGN_KO.md)을 작성하고 자체 검토했다. 승인 후 격리 worktree/별도 build를 준비하고 상세 실행 계획 및 구현으로 이어간다. 이 조사에서 기존13.6 파일 수정, stage/commit/push, 새 패키지·engine 생성/실행을 하지 않았다. 기존213 PASS·v13/v14 성공/실패는 과거 범위로 보존한다.
