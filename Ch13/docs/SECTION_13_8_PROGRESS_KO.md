# SDD ledger — plan: Ch13/docs/SECTION_13_8_PLAN_KO.md

2026-11-04 KST. 단일 작업자. 현재 M0 완료, Task 1 시작. 구현·물리 성공은 아직 없다.

## M0 확인

- 첨부 원고 제목: 13.8. 복합 시뮬레이션 프로젝트 실습 및 검증. 사본 work/section_13_8_preparation_20261104/MANUSCRIPT_13_8_KO.txt, SHA256 7bb525cc721baf36a37a7af24042e348f1588060dce327c5de4fafb474986d2b.
- 기준 HEAD 13ecb58d346f38778ac8015d3c2321d20c9971e0; v7 manifest hash 2f024c9362e1ab5d50d8c6cac7163ef0c6bc6daedff928a3338a65748ce6a179 재확인. 기존 worktree에는 인계 문서만 untracked.
- GitHub 연결 도구 branch/PR 검색은 각각 빈 결과. 직접 ls-remote는 네트워크 실패. main 최신 HEAD는 이번에 확인하지 않았다.
- boot ID 3c49dfdb-f65d-41c9-8574-f6119b7175e5. 현재 프로세스 전체 조회 및 기존 inspect_r2_residuals.py PASS: owned_stack_matches=[], engine_lock_free=true. domain163 daemon은 다른 작업이며 보존. 결과는 preparation/INITIAL_RESIDUAL.json. 이는 조회 시점 증거다.
- 설치 dpkg: moveit-core 2.12.4, moveit-msgs 2.6.0, rosbag2/rosbag2-py 0.26.11. 13.8 build 후보 absent.
- native create_worktree는 sourceRoot가 chat workspace root가 아니라는 오류로 미지원. 사용자 지정 sibling 후보를 Windows git worktree add로 생성, 기준 13ecb58d, branch feat/ch13-section-13-8. 원본 인계 문서는 자동 포함되지 않음.

## 공식 패턴 조사

1. [MoveIt 2.12.4 planning_scene_interface.cpp](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/planning_interface/planning_scene_interface/src/planning_scene_interface.cpp)를 연결 GitHub로 읽음. applyPlanningScene 서비스 응답과 attached/world collision object 처리를 참고한다. C++ 예제의 nested spin은 기존 Python owner에 복사하지 않는다. planning attach는 물리 부착이 아니다.
2. [rosbag2 0.26.11 simple_bag_recorder.py](https://github.com/ros2/rosbag2/blob/0.26.11/rosbag2_examples/rosbag2_examples_py/rosbag2_examples_py/simple_bag_recorder.py)를 읽음. SequentialWriter, StorageOptions, TopicMetadata, CDR 직렬화, node clock timestamp 패턴을 확인. 설치 버전과 일치. 기존 원본 관측 나이를 bag receipt로 덮어쓰지 않는다.
3. [ROS Jazzy QoS override 원본](https://github.com/ros2/ros2_documentation/blob/665b15d970cd1ee8a2d0301c673159a3c5092228/source/How-To-Guides/Overriding-QoS-Policies-For-Recording-And-Playback.rst)을 조사. topic별 compatibility와 --qos-profile-overrides-path를 채택 후보로 기록. 모든 제어 토픽을 Best Effort로 일괄 전환하지 않는다. docs.ros.org 본문은 접근 차단되어 공식 GitHub 원본으로 대체.
4. 기존 SECTION_13_7_RESEARCH_KO.md의 py_trees_ros 2.6.0 및 rclpy 비동기 cancel/result 패턴을 재사용한다. 문서·코드 존재는 로봇 물리 성공 증거가 아니다.

## Pre-flight

Task 1→3/4: trial schema와 sim/wall 정의를 공유. Task 2→4: phase/예약 goal 및 engine 관측 계약 공유. Task 3→4: bag·계측 결과를 trial로 집계. 인터페이스 불일치 없음; 실제 연결에서 새 발견은 아래에 기록한다.

Ruling: 사용자 '질문없이 권장 방식으로 진행'에 따라 설계/계획 확인 질문을 생략한다 — 전체 원고를 목표로 단계적 구현 — 잘못 해석하면 scope 조정 비용.

Ruling: 사용자 단일 작업자 지시를 우선하여 subagent와 독립 reviewer를 사용하지 않는다 — 자체 검토로 한계를 명시 — 독립 검토보다 결함 탐지력이 약함.

## Task 1~3 개발 중

신규 판정/경로 17 PASS; 운반+기존 lease 39 PASS; 계측 포함 42 PASS; 비객체 heartbeat 예외를 재현·FAULT 처리한 신규33 PASS. 부품 시험 숫자는 서로 포함 관계이며 합산하지 않는다.

초기 venv에는 pytest 직접 import가 없었다. 기존 env.sh bootstrap 뒤에서는 시스템 pytest를 찾으며 venv NumPy 우선순위를 유지한다. 전역 설치 없음. 초기 build는 별도13.8 경로에 기존6+BT1+새1 패키지 성공.

새 부품 driver의 multiprocessing main 재진입을 발견해 소유 시험만 SIGINT로 중단(46 PASS 뒤 중단, 완전 PASS 아님). 진입점 보호 뒤 첫 전체회귀는269 PASS/3 FAIL/116.70초. 실패: test_renderer_delivery_does_not_depend_on_blocked_parent_retention[True], test_child_bootstrap_exit_is_distinguished_from_a_live_warmup_timeout, test_child_initialization_failure_is_reported_before_camera_is_returned. 기존 제어/임계값을 바꾸지 않고 실행 환경을 조사 중. 하나는 importlib 수집 module의 ros2_ws namespace가 child에서 import 불가, 둘은15초 초기화 예산 중 spawn에13.58초가 걸려 ros_import_begin에서 만료. 카메라 deadline을 늘려 통과시키지 않았다.

공식 [Jazzy rclpy action/client.py](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/action/client.py)의 send_goal_async(goal, feedback_callback=None, goal_uuid=None)를 읽고 사전 UUID 예약을 사용한다. cancel/get_result future를 별도 추적한다.

카메라 시작의 같은 실패가 두 최소 수정 후에도 남아 실행 경계를 검토했다. 동일 hash native 사본에서 시작3개가2.80초 PASS로 바뀌었다. Windows mount의 test module/namespace import 비용을 분리한 것이며 camera startup15초·제어·수명은 변경하지 않았다. 이어 native 전체는277 PASS/1 FAIL/32.13초: 기존 test_actual_totg_boundary_derivatives_can_end_in_bounded_hold가 읽는 과거 moveit_probe.json fixture를 사본에 빠뜨린 것이 원인이다. 해당 원본은 수정하지 않고 hash 확인 사본으로 보완했다. 불완전한 snapshot 결과를 전체 PASS로 보고하지 않는다.

실제 설치 감사 v1: navigation34·manipulation24·BT6·4개 Python 패키지52모듈 바이트 일치 및 외부94자산 hash PASS. 실제 venv child NumPy 우선순위 PASS. v1 source freeze305개/자산94개, SHA256 214c325c1ca84ee5c54001abbb7824a8c963753602901b2c37fe82258dc54439는 구현 전후 preflight 동결이며 아직 engine 실행에는 사용하지 않았다.

Ruling: 장시간 Windows 경로에서 시험을 반복하는 대신 별도13.8 build의 hash-checked native 사본에서 부품을 실행한다 — 동일 바이트와 fixture hash를 기록하고 외부 자산/공유 lock은 원본 링크 — 사본에서 빠진 실행 의존성이 있으면 그 시험을 실패로 기록하고 사본 구성을 보완해야 함.

Task 1: complete — separate8-package build; 278 component tests PASS/34.47s in hash-checked native source snapshot; installed53 Python modules/94 assets audit PASS, actual child NumPy priority PASS. First physical case source v2: 308 files/94 assets, manifest SHA256 7f7a2c7caff92d63eeec33f997790a2462dbf667ee2c3460889e6eb0ce1a8012. Task 2: in_progress — physical acceptance pending. Task 3: in_progress — metrics component green; live bag/replay pending.

## v2 첫 실제 사례: FAIL 보존

UUID a96cd6d7-9805-41ce-9dff-4c13916e4653. BT FAILURE, worker joined, launch12개 clean exit/잔여0, 정상 engine shutdown/rx/upstream join PASS, 사후 공유 lock free. 파지 자체는 최소100.016mm·2.20sim초 hold·양 접촉100%·상대 slip0.02754mm PASS. 귀환 회전14.60sim초/731samples 동안 양 접촉100%·최대 slip4.274mm, 대상 z0.627~0.662m. 이후 gripper 부분 가림으로 upright fit 높이75% 기준을 만족하지 못해 OBSERVATION_EXPIRED로 정지. 낙하 성공/귀환 성공으로 집계하지 않는다. trial은142.07sim초/402.73wall초, CPU42.81%/8 allowed cores, 최대 tilt0.04282rad. --no-bag 개발 사례다.

현재 코드 변경 전에 당시308개 소스 바이트를98a6523f에서 동결 hash와 전수 대조해 source_v2/runtime_source.tar.gz로 보존했다. archive SHA256 36d75c253f4e884f7af952b30971e05d1aa9b1f34a1aa562b59543f71aa7d3fb. 사후 보존이며 새 실행이 아니다.

Ruling: 고정 팔 운반은 만료된3D point를 갱신하는 대신, 원본300ms capture health + 매 physics step의 지정 양 finger 접촉/force-hold + 예약 Nav goal로만 권한을 부여한다 — 새 팔 계획/개방은 금지하고 PLACE에는 fresh3D를 다시 요구 — 접촉 센서/카메라 health와 object identity 연계가 잘못되면 운반 중 시각 추적 공백을 놓칠 수 있어 별도 DDS/만료/소유권 시험과 실제 재검증이 필요.

새 관측/phase/비유한 물리값5개 RED 확인 후 보완. native capture-health 채널은 실제 설치 전 RED 확인. C++ latest-only relay 추가/동일 설치 감사 후 전체287 PASS/34.13초. 기존 stationary lease와 기본 nav 회귀를 포함한다. LOWER→RELEASE→RETREAT 순서·PLACE yaw drift·contact force finite 거부도 보완했다.

받침대에 내려놓을 때 planning attached target와 지정 reuse_receiving_support 사이만 ACM 접촉을 허용해야 한다. 기존 검증된 Planner.allow_fingers의 GetPlanningScene→symmetric ACM diff→ApplyPlanningScene 패턴과 공식 MoveIt2.12.4 서비스를 재사용한다. 다른 robot/world 규칙 유지·원본 matrix 비변경·해제 복원 시험 RED 후 추가 구현. 물리 부착은 하지 않는다.

공식 MuJoCo3.13.0 python/mujoco/specs_test.py를 읽어 MjSpec.add_body/add_geom·size·quat 패턴을 확인했다. Level2 경사 fixture의 후속 기하 구현 근거이며 아직 해당 월드 물리 성공이 아니다.

정적 수명 검토 보완: 귀환도 기존 OwnedClient factory를 전달받아 send future부터 소유한다. fault/예외 시 직접 cancel future를 버리지 않고 GoalTracker가 늦은 수락·result와 ACK 완료까지 회수한다. result가 ACK보다 먼저 도착하는 실제 future 순서 시험 RED→GREEN. 전체289 PASS/35.34초, 전용5-package rebuild PASS, 설치54모듈/94자산/child 감사 PASS. v3는 실제 실행 전 preflight 동결이며 engine 실행하지 않았다. 두 번째 실제 사례는 v4 소스312/자산94, SHA256 a3fe04e32c0b033ac4de76262964e609b9fb428a8d31ab331ff7a5bcfaac66e9를 사용한다. UUID34f5ef1d-8fee-4d81-913b-fa76a3945a47, 이번에는 선별 rosbag 기록을 포함한다.
