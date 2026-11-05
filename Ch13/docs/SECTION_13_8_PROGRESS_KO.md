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

## v4 두 번째 실제 사례: FAIL 및 기록/재생 검증

UUID34f5ef1d-8fee-4d81-913b-fa76a3945a47. 물리 파지는 최소100.229mm·2.18sim초 hold·양 접촉100%·상대 slip0.02730mm PASS. 귀환 Nav2 terminal6 ABORTED, navigation fault VISION_EXPIRED. 실제 비전 node fault는 비어 있고 accepted5327, 거부1은 capture/clock/TF expired였다. v2의 원통 fit 가림 실패와 구분한다. worker joined/12 child clean exit/잔여0/정상 engine shutdown/rx/upstream join/사후 lock free. trial146.08sim초/414.07wall초·CPU43.89%(8cores)·최대 tilt0.03661rad. 미션 성공으로 집계하지 않는다.

health_failure_analysis.json: 마지막 사용 capture는4491.01159245wall, navigation fault 결정은4491.313861819wall로 source 나이302.269ms. 그 사이 새 capture4491.081034455는4491.297060049에 실제 RGB-D/과거TF 검증을 마쳤지만 기존 혼합 FIFO 경로에서 만료 판단 전 반영되지 않았다. 기존 TTL을 늘리지 않고13.8 opt-in에서만 독립 latest-only native health lane으로 분리한다. native 최초 receipt와 Python 처리 시각을 상태에 추가하고 기존13.6/13.7 기본 경로는 유지한다. 귀환 재진입에는 source 나이≤100wallms의 추가 여유를 요구하며 source time을 바꾸지 않는다. 이 구조와 재진입 조건 RED→GREEN; 전체292 PASS/32.00초.

실제 bag는 정상 close, MCAP131424메시지/필수12토픽/5327관측 payload/record time/metadata count 일치 PASS. 별도 domain136에서 /tf_static419·관측5327·capture health5882·BT log4148·player clock592개 수신,16.46wall초 PASS. 이것은 sensor/BT reception 재생이며 mission 성공이나 전체 비전/Nav2 알고리즘·실기 재생 검증이 아니다. actuator·live lease·start 명령은 재생하지 않았다. 영상 compressed topic은 없고 bag에 raw RGB-D 전체를 기록한 것도 아니다.

v4 소스312바이트 집합은00fafb0a에서 hash 확인 사후 보존했고 source_v4/runtime_source.tar.gz SHA256 d230f0f10547313df113f5f5ee296fda143b69321d62f4c18af65e1469c3f5ce이다. 기존 v2 source/FAIL/verdict는 보존한다.

Ruling: fresh health가 renderer→검증 단계에서 유효해도 혼합 navigation FIFO 지연으로 만료될 수 있어 native queue를 분리한다 — 기존300ms/원본 capture·receipt 유지 및 기본 경로 보존 — renderer 자체의 진짜300ms 손실은 계속 FAIL이며 분리만으로 모든 실시간 변동을 해결했다고 주장할 수 없음.

공식 rosbag2 0.26.11 rosbag2csv.py(blob0a03ed86ca90d2d66ef6bf08d1fb9b744e297415)를 읽어 SequentialReader/StorageOptions/ConverterOptions/type map/deserialize_message 패턴을 적용했다. 실제 MCAP fixture의 기록 검사 및 필수 토픽 누락2개 시험 RED→GREEN. ROS node를 시작하지 않는 inspect_recording.py와 별도domain replay_recording.py를 제공한다.

## 재개 및 세 번째 실제 사례 준비
이전 v5 최종 시험/감사는 자동 승인 검토의 사용량 한도로 실행 전에 중단됐었다. 사용자 작업 재개 지시 후 소스와 잔여를 확인했다. 재개 suite294 PASS/44.00초·설치55모듈/94자산 PASS. WSL cold boot가 바뀌므로 실제 실행 전 boot ID/공유 lock을 다시 기록하며 시스템 설정은 변경하지 않는다.

정적 receiving camera 검토에서 기존x=-0.55m 위치의 원통 경계가320px 화면의x312~384로 벗어나는 RED를 확인했다. 카메라/원본 모델/정책/PD를 바꾸지 않고 개발 fixture 수령점을x=-0.80m,y=0m,지지면z=0.50m로 옮겼다. static projection과 전체295 PASS/37.48초,5-package rebuild17.5초,설치56모듈/94자산/child audit PASS. 이는 정적 시야 검증이며 실제 place 성공 증거가 아니다. v2/v4의 원래-0.55m fixture와 결과는 보존한다.

Ruling: fresh3D가 필요한 place 위치는 기존 카메라의 시야를 유지하도록 fixture를 배치한다 — 기존 팔 길이/카메라/원통을 유지하며x=-0.80m 채택 — 원고(0,0)는 robot return goal이며 실제 수령 받침대 좌표는 별도 공개; 이 정적 확인만으로 가림/도달/물리 성공을 보증하지 않음.

v5 source320/assets94, SHA256 a8a3a1fa258b05633110ef3b280aa7cdff20fd2387b4f25db8a1ccd391d3b8c1. 세 번째 사례 UUID1499904c-2d19-4010-a499-03919ecdc832, 선별 bag 기록 포함, 실제 인수 대기.

## v5 실제 결과 및 재개 후 진단

세 번째 사례는 전체 FAIL. pick 최소100.493mm·2.22sim초 hold·양 접촉100%·상대 slip0.02780mm PASS. Nav2는 terminal4 SUCCEEDED, 마지막 실제 base 위치(0.01362,-0.01847)m였지만 yaw2.24356rad로 예약 목표pi와 달랐다. 이어 PLACE_WAIT에서 fresh3D를 얻지 못해4wall초 만료. 비전 fault는 비어 있었고 accepted4847/rejected527; 마지막 거부 원인은 원통 upright 높이 가시성 부족이었다. trial160.496sim초/415.889wall초·CPU46.05147%(8cores)·최대 tilt0.044578rad, bag 정상 close. worker join·12 child clean exit·잔여0·공유 lock free. 위치 도달만으로 귀환/미션 성공을 선언하지 않는다.

원인1: continuation의 귀환 quaternion에서z만1로 대입하고 ROS 메시지 기본w=1을 남겼다. 설치 NavigateToPose.Goal의 실제 기본값으로 재현했고 norm=sqrt(2)인 잘못된 입력이다. 공식 Jazzy Quaternion-Fundamentals의 전체(x,y,z,w) 설정·unit norm 패턴을 적용해 yaw/2의sin/cos를 모두 설정한다. 새 goal 생성 시험은 함수 부재로 RED, 수정 후 단위 norm·pi yaw·원본 stamp와 잘못된 정착 자세의 독립 차단2개 PASS/12.53초. fresh3D 대기 중에도 실제 자세 불일치는 즉시 PLACE_POSE_MISMATCH로 latch한다. quaternion 수정이 가림까지 해결한다는 근거는 없어 저장 RGB-D를 먼저 분석한다.

v5의320개 당시 소스는a7786a05에서 전수 hash 대조해 source_v5/runtime_source.tar.gz로 사후 보존했다. SHA256 6109993d775026f4d3559c68e83b91d292a7bbe98bd804e5306eca7627fae363. 원래 증거/동결/FAIL은 보존하며 새 실행으로 간주하지 않는다.

### 같은 가림 실패의 구조 검토

두 차례 가림 실패 후 저장 자료에서 camera/hand 시야 관계를 검토했다. 공식 PCL cylinder segmentation의 평면/원통 분리와 반경 제한 패턴을 조사했지만, 저장 영상의 아래 뚜껑 후보는 robust plane의 충분한 inlier/축 안정성을 얻지 못했다. 따라서 partial cylinder detector를 runtime에 넣지 않았다. 기존 fit의75% 높이·1.5mm residual과300ms 수명을 낮추지 않는다.

별도 정지 렌더링 도구 check_camera_mounts.py로 v5의 기동/파지/운반/정착8개 실제 저장 qpos를 비교했다. 물리 step·actuator·live ROS 권한 없이 기존 Renderer의 paired RGB/depth와 동일 geomgroup/그림자 설정을 사용한다. 최초 비교는 group5를 표시하지 않아 전부 target missing이었으며 해당 로그도 보존했다. 이를 바로잡은15개 고정 mount 비교에서 높이0.35m·pitch down5도 후보는8개 모두 기존 엄격 fit을 통과했다. 부품 회귀에는8개 상태의 qpos만 읽기 전용 fixture로 동결하고 추정값의 사후 oracle 오차≤4mm를 확인한다. oracle는 추정 함수 입력으로 쓰지 않는다.

Ruling: 새로운 부분 가림 추정기를 추가하는 대신13.8 carry_v1에서만 camera base 위치를(0.4,0.25,0.35)m, yaw=-20도·pitch down5도로 고정한다 — 기존 카메라보다10cm 높이고 엄격한 기존 검출·TF/수명 계약을 유지하는 작은 설정 변경 — 실제 해당 mount와 다른 카메라 설치에는 이 결과를 적용할 수 없고 정적 렌더링만으로 연속 물리 성공을 보증하지 않음. 기존13.6/13.7 기본 mount는 그대로 둔다. 이전의 카메라 유지 판단은 이 구조 검토로13.8 opt-in에 한해 변경한다.

공식 MuJoCo3.13.0 doc/XMLreference.rst의 body/camera fixed·body-relative pos/quat와 -Z view/+X right/+Y up을 연결 GitHub에서 확인했다. 컴파일 전 MjSpec camera 설정과 기존 SensorSuite의 compiled extrinsics→ROS optical TF 패턴을 사용한다. 카메라 위치를 실행 중 물체에 따라 이동하거나 오래된 영상을 새 capture로 바꾸지 않는다. 저장 시야 회귀는 기존 배치에서 RED(1 failed/1 passed,6.34초)를 확인했다.

v6 전체 부품299 PASS/49.03초·5-package build18.8초·설치56모듈/외부94자산/child 감사 PASS. 실행 전 소유 stack0·공유 lock free·boot5d88983d-6bab-4532-93f2-7ea991a80ff5를 확인했다. source323/assets94, SHA256 2deed5c8c159818eb96298606a283228d02d08abcca1021b436c84b3611d3ee0. 다음 네 번째 실제 개발 사례 UUID13ef4150-a1fc-4a55-8a47-f697f5507449, 결과 대기. 이전 v2/v4/v5 실패를10회 고정 설정 평가에 섞지 않는다.

### v6 시작 관측 실패

네 번째 실제 사례는 이동/파지 전 select_goal의 기존8wall초 준비 조건에서 FAIL했다. fresh actual RGB-D observation/TF/map를 확보하지 못했고, 비전 accepted0/rejected0/fault비어있음, camera_receipts.jsonl와camera_health.jsonl도0바이트였다. renderer는192개 캡처·정상 join/exit0였다. 따라서 이를 원통 기하 fit 거부나 카메라 시야 실패라고 단정하지 않는다. raw DDS 수신/receipt 매칭/TF별 세부 카운터가 없어 그 경계를 아직 구분할 수 없다. 다음 확인에는 관측 node의 읽기 전용 callback/pending/matched/TF 카운터만 추가하며 기존8초/300ms를 늘리지 않는다.

trial은4.76sim초/11.460wall초·CPU33.856%·tilt0.015058rad·bag close true. worker join/12 child clean exit/잔여0/공유 lock free. 실행 boot98db521c-8b39-496a-a45c-437550a9e03e로 preflight 이후 WSL cold boot가 바뀌었다. stale PID를 회수하거나 lock을 삭제하지 않았다. v6의323파일은ba17d27d에서 hash 확인 사후 보존했고 source_v6/runtime_source.tar.gz SHA256 b171287b9ba37b1a6c3d07a03511a178a4daa553e61f74dad4a8612e1d1f6f61이다. 물리 성공으로 집계하지 않는다.

관측 전달 진단만 추가한 관련46개 시험 PASS/14.58초,5-package rebuild13.0초·설치56모듈/94자산/child PASS. v7 source323/assets94 SHA256 a3a5c7c09e8379762b2bea7eee98cd5d6402fb050b5383c3d9c08de914ecc1ac. 실행 전 boot3e437ed6-8cf7-4c43-a790-330e49bda312·소유 stack0·공유 lock free. 다음 실제 사례b91a740e-a75f-4acb-b4fe-3cd5f68ad8b6는 새 진단을 포함하며 제어/카메라/시간 한도는v6와 같다.

### v7 준비 action 뒤 heartbeat 공백

v7은 새로운 관측545개, 각 raw camera callback615개·matched2388샘플·TF120샘플로 시작과 이동을 통과했다. 비전 fault/rejected는 비어 있고 실제 파지 전에 준비 arm/그리퍼3개가 각각SUCCEEDED했다. 이후 run_pick의 첫 개방 요청이 거절되어 FAIL. 별개 시작 실패v6를 수정 완료했다고 쓰지 않는다.

마지막 정상 heartbeat sequence296 send267.577104420wall→297 send267.976799706wall 사이399.695ms 공백이 있다. engine은267.879890042wall에 MISSION_EXPIRED를 latch했다. 관측은 계속 새로 처리됐으므로 카메라 만료와 구분한다. 준비 action 마지막 terminal267.587729821 이후 Planner·새 gripper client 초기화 경로에서 ROS owner가 heartbeat를 충분히 돌리지 못했다. 실제 어느 초기화 하위 호출이 시간을 소비했는지는 기존 로그에 없으므로 특정 파일 I/O가 유일한 원인이라고 단정하지 않는다.

동기 Planner description lookup/read에400ms 지연을 주는 부품 시험에서 실제 owner polling 공백400.55ms로 RED를 재현했다. 기존 Planner.compute의 작업 스레드+owner until 패턴을 초기화 description 읽기에도 적용한다. ROS entity 생성은 계속 원래 owner에서 수행한다. 초기화 하위 단계와 gripper 승인/거절 시각·phase/busy/reserved/fault를 다음 자료에 추가해 남은 원인을 구분한다. 300ms 수명·한도·물리 제어를 늘리지 않는다. 변경 후 전체300 PASS/43.98초(세부 시각 기록 추가 전); 추가 기록은 개별 재확인한다.

trial17.70sim초/41.652wall초·CPU43.734%·tilt0.034776rad, bag close·worker join·12 child clean exit. 실제 파지·운반·내려놓기 성공이 아니다. v7의323파일은0f0416b1에서 hash 확인 사후 보존했고 archive SHA256 24962e57095ac72ff02586fd59034161d8fc8e8c3f65a75804f6d0ca42a377ba이다.

v8은 관련 action/그리퍼/회수17 PASS/3.66초, 전체300 PASS/43.98초, 초기화 세부 시각 기록 후 지연 시험1 PASS/4.91초.5-package rebuild19.3초·설치56모듈/94자산/child PASS. source324/assets94 SHA256 11762c18c95f7fc5e4d41240a5538342b449a469d402476e7e6721ae49a05260. 소유 stack0·공유 lock free를 다시 확인했다.

Ruling: 실제 runtime도 전수 hash가 같은 WSL native source snapshot을 사용한다 — Windows mount의 source 접근을 hot path에서 줄이고 기존 단일 owner/파일 바이트/정책/설치본을 유지 — 복사본의 상대경로·자산·잠금 연결이 달라질 위험이 있으므로324파일 hash 및94자산 freeze를 재검증하고 두 symlink의 realpath가 원래 sibling 자산·공유 lock과 같은지 확인한다. 증거 출력은 원래 worktree의 새 UUID로 지정하며 이 복사는 물리 실행 증거가 아니다. 준비 도구·경로는 section_13_8_preparation_20261104/runtime_stage_v8.json에 보존한다.

native 사본/home/jinho/ch13_reuse_13_8_build/live_source_b1b1649ca2ff470d801d15f94eadb728/repo의324소스·94자산 동결 검증 PASS. 자산과lock realpath가 기존 work/ 아래 원본과 같음을 확인했다. v8 실제 개발 사례UUIDe1c738a7-42a2-417b-9e66-4aa445bd9875를 시작하며 결과는 원래 worktree에 남긴다. 소스commit8bf25e10이며 아직 성공 판정이 아니다.

### v8 접근 중 가림 실패 및 검증 표본 보완

v8은 초기화/준비 action을 통과했지만 실제 파지 전 GRASP_APPROACH 도중370.036915580wall에 OBSERVATION_EXPIRED로 정지했다. 비전 accepted3027·높이 가시성 부족 거부56·fault비어있음. trial100.56sim초/240.879wall초·CPU44.443%·tilt0.034256rad·bag close. worker join/12 child clean exit·engine/rx/upstream join·잔여0·공유 lock free. 이 실행은 파지·귀환·내려놓기 성공이 아니다.

초기화 실측: description 읽기/poll1.507ms, arm client9.584ms, service 생성59.214/2.381/13.663/2.716ms, pick gripper client10.765ms. 이는 이번 native 실행의 수치이며 이전v7의 어떤 하위 호출이399.695ms를 소비했는지 소급 입증하지 않는다. v8 당시324파일은8bf25e10에서 hash 확인 보존했고 source_v8/runtime_source.tar.gz SHA256 5610e2751299b0fc4f76cb93dc960637fb2121793c9267514b2dcb35236ed9c2이다.

이전8개 시야 표본은 접근 중간 자세를 충분히 포함하지 못했다. 정적 회귀의 표본 선정 결함을 인정하고, v5 성공 파지/운반 궤적과v8 실제 접근 실패 궤적 전체를 사용해 보완한다. 원본2초 간격134자세·16개 고정 mount 비교에서(0.4,0.4,0.3)m 후보만134/134 fit과 사후 오차4mm 이내를 통과했다. 그러나0.1sim초 간격2653자세 재확인에서는v5 106.72sim초의 단 한 자세에서 기존75% 높이 가시성에 못 미쳤다. 이를 전수PASS나 여유가 있는 시야로 표현하지 않고 경계 구간을 추가 확인한다. 새 회귀 fixture는0.5sim초 간격532자세와 원본 로그hash를 보존한다. 아직 runtime mount를 다시 바꾸지 않았다.

후속 경계 비교: 전체0.5sim초 간격+100~112sim초 구간0.05sim초 간격747자세,6개 작은 위치 차이 후보를 확인했다. 최소 변경 후보(0.4,0.4,0.29)m·yaw=-31.607502도·pitch0은747/747, 최소 visible height71.177mm(원통80mm의88.97%), 사후 위치오차최대1.545mm였다. 이를 두 전체 궤적의0.1sim초 간격2653자세로 다시 확인해2653/2653, 최대 사후 오차2.580mm를 얻었다. camera mount 외에 기존 fit/물리/한도/TF·capture 수명은 바꾸지 않는다. 초기134자세 비교만으로 인수하지 않았고, 실제 동작의 새로운 팔 경로·보행 변동은 여전히 추가 확인 대상이다.

532자세 회귀는 기존v6/v8 camera에서 RED(1 failed/1 passed,6.44초)를 확인했다. critical 구간까지 포함하는747자세 fixture를 별도로 추가하며 원래8/532자세 자료도 보존한다. Runtime mount는 위 최소 변경 후보로 갱신하고 기존 default camera 유지 시험과 함께 전체 회귀 중이다. 모든 렌더링은 engine 종료 후 저장 상태에 대한 관측 시험이며 새 물리 실행 성공이 아니다.

새 mount/747자세 회귀·원래 default camera 유지·기존 수명/취소/수치 판정 포함301 PASS/49.60초. 다음 실제 사례는 새 v9 동결과 native source 사본으로 격리한다. 원래 v8 FAIL·초기8자세 표본 한계·중간2652/2653 결과는 그대로 보존한다.

v9 준비 첫 시도는 일회성 Bash 스크립트의 Windows CRLF 때문에line2에서 시작 전 중단됐다. LF로 정규화한 별도 retry 로그를 보존했고 engine은 그 실패 시도에서 시작하지 않았다. 이후 build·설치56모듈/94자산/child 감사 PASS. v9 source326/assets94 SHA256 7a08ea204ffc5d4b682712cd6f1213e63dc783af4313a65cff3e54e06cd586a9, native 사본/home/jinho/ch13_reuse_13_8_build/live_source_5c1a8ce1dde440e0b622259f216947b6/repo에서 전수 재검증 PASS. 자산/공유 lock realpath 동일. 다음 실제 사례f50ddb77-4c68-4e37-8e0c-df8c9fae07a9, 원래 worktree에 새 증거를 기록한다.

v9 실행 대기 중에는 고정 native 사본/설치본/자산을 수정하지 않는다. 후속 배포용 runtime staging·model 제외 raw archive의 시험 명세만 원래 개발 worktree에 신규 작성한다. 아직 구현/RED 실행 전이며 v9 source326에 포함되지 않는다. engine 종료 전 pytest/build/대용량 분석을 실행하지 않는다. 이후에는 새 소스 동결로 구분한다.

### v9 실제 결과와 검출 실패 원인의 재분류

v9도 GRASP_APPROACH 중259.704448950wall에 OBSERVATION_EXPIRED로 FAIL. trial104.84sim초/239.398wall초·CPU43.223%·tilt0.035119rad·bag close, worker join/12 child clean exit/잔여0/공유 lock free. 원통 파지 전에 중단됐다. 실제 관측3080·높이 부족으로 표시된 거부11·capture/clock/TF expired1. 원래326파일은1aafc599에서 전수 hash 보존했고 source_v9/runtime_source.tar.gz SHA256 3154c6c59211caa5a8fea833b0c98e250a633e28381f3e336735a09714405fb8이다.

같은 실패가 남아 camera 위치를 더 바꾸지 않고 원래 검출기의 조건을 분해했다. 마지막 frame은 빨간 위/아래 조각199/191pixel, 합친 높이79.695mm·xy centroid 거리1.623mm로 기존 결합 gate를 통과한다. 그러나 결합 후 실제 거부 원인은 높이가 아닌 surface RMS였다. robust center의q90 오차0.0829mm인데 소수 경계 점의 반경이34.701mm까지 튀어 전체RMS1.50279mm로 기존1.5mm를 넘었다. 기존 예외 처리가 결합 후 원인을 버리고 첫 단일 조각의 높이 부족만 보고해 진단을 흐렸다. 대상은 같은 시각 tilt0.00077rad·finger 접촉0이어서 실제 기울어짐/접촉에 따른 모양 변화가 아니었다.

원본 frame의 bool mask를3x3 한 번 erosion한 부품 분석은 위/아래140/133pixel·관측 높이74.388mm·기존 strict circle RMS0.0460mm·사후 중심 오차약0.38mm였다. 원래 RGB-D·capture/TF·표면 임계값을 유지하며13.8 opt-in에만 내부 pixel 선택을 적용한다. 결합 실패 이유도13.8에서는 실제 결합 fit 오류를 보고한다. 원본 actual frame의 기본 fit 거부와 새 API 부재2개 RED를 확인했다. 기본13.6/13.7 detector는 변경하지 않는다.

후속 배포 도구는 구현 전 collection RED2개를 확인했다. 새 staging/archive 구현 후 실제 기존13.6 restorer를 통한 빈 폴더 복원을 포함해 관련12 PASS였고, 같은 실행의 새 boundary 시험2개는 예상대로 RED였다. 아직 새 boundary 구현의 최종 GREEN/전체 회귀는 진행 중이다.

단순 mask erosion은 actual frame 부품14 PASS 후 전체 회귀에서312 PASS/2 FAIL(원거리 원통의 정상 side 폭까지 감소,40.40초)이었다. 이를 임계값 조정으로 통과시키지 않고 boundary를 식별한 뒤3x3 red/valid-depth 이웃 중간값보다5mm 이상 앞서는 측정만 제외하도록 좁혔다. v9 실제 frame은117개 경계 중1pixel 제외 후 작은 조각4pixel도 기존 최소20pixel gate로 제외됐고,349개 side점·높이78.996mm·strict RMS0.0497mm가 됐다. 기존 기준/정상 silhouette와 raw capture는 유지한다. 새 경계 처리 및 기존 원통/전체 저장 자세 관련12 PASS/12.96초. 전체 재확인은 아직 대기다. 자세한 출처·자체 적용 차이는 RESEARCH의 경계 처리 항목에 있다.

v10 후보 전체314 PASS/48.87초. 공개 스크립트 stage_runtime.py와 archive_evidence.py를 추가했다. staging은 새 build 아래 전수 source/asset hash와 같은 shared-lock realpath를 확인하며 별도 native freeze 검증을 거친다. archive는 명시된13.8 UUID 폴더만 받고 engine lock이 사용 중이면 거부하며 원본을 삭제하지 않는다. 기존13.6 restorer로 빈 폴더의 실제 바이트를 복원하는 시험도 PASS. 실제 기존7개 개발 FAIL의 archive와 새 설치 감사/동결/native staging을 준비 중이며 아직 새 물리 결과가 아니다.

v10 preflight:5-package build14.0초·설치58모듈/94자산/actual child PASS. 기존7개 실제 FAIL 원본을 유지하면서 각각15.1/40.0/42.2/2.3/5.8/26.4/27.3MB 모델 제외archive를 만들었다. v9 실제27,333,891byte archive SHA256 f87567eb886c519858b519ebdd845aae0356b69807552392deaf4bec52e717eb를 새 빈 폴더에41파일 hash 복원 PASS. trial/BT/nav/source 원본hash와FAIL 보존. raw archives는 로컬에 남기고 선택 commit에는 source·요약·manifest·감사 근거를 남긴다. 원격 게시 검증이 아니다.

v10 source336/assets94 SHA256 3e697f62ef429ae82cd4f82d54636898fea055a33f67576eb03d115ed21db832. 공개 stage_runtime.py로/home/jinho/ch13_reuse_13_8_build/live_source_cfbc43c12f9e4b6eaf74d0a043f021dd/repo를 만들고 native source/94자산·shared lock 동일 realpath를 검증했다. 다음 실제 개발 사례UUID8478db34-ae8b-465f-9337-96bcb615defe. source 변경과 archive/오프라인 복원만으로 성공을 주장하지 않는다.

### v10 실제 두 사례와 내려놓기 후 장면 경계 수정

8478db34-ae8b-465f-9337-96bcb615defe는 startup FUTURE_SOURCE:joints로 FAIL. 새 검출기를 시험할 파지에 도달하지 않았다. trial11.318sim초/25.118wall초·CPU34.804%·tilt0.01506rad·bag close. 동일 동결의 별도 UUID614e67e5-5aac-4ec0-ad89-1664021c2d95 재시도도 전체 FAIL이며 두 실패를 모두 보존한다. 첫 사례를 성공률 분모에서 제거하지 않는다.

614e 사례는 pick 최소100.418mm 상승/2.18sim초 유지/양 finger 접촉100%/slip0.02731mm PASS. 같은 engine에서2.54233m 운반, 정상 yaw 귀환·실제 정착·새 RGB-D로 PLACE 진입, LOWER·지지 접촉·실측 gripper0.0300755m 개방/접촉0까지 실행했다. 최종 원통(-0.798639,-0.017372,0.539891)m·support0.196212N. 그러나 RETREAT Cartesian fraction0으로 중단돼2sim초 post-release hold가 부족했고 전체 FAIL이다. base 귀환 오차0.052002m는 원고3cm 목표를 넘으며 유지한다. trial190.64sim초/397.697939wall초·CPU43.101%·tilt0.039292rad·bag close,12 child clean exit/worker join/공유 lock free. 물리 transport의 placed_hold만 false이나 이는 전체 성공 증거가 아니다.

정확한 원인은 attached parent 불일치였다. ADD는reuse/tcp인데 REMOVE는reuse/link6을 지정했다. launch.log의 MoveIt 오류와 공식2.12.4 planning_scene.cpp REMOVE 분기를 확인했다. 바깥 ApplyPlanningScene.success만 true여도 안쪽 REMOVE는 거부될 수 있다. 이후 MANIPULATION_GRAPH_LOST는 실패 회수 도중의 후속 현상이다.

Ruling: ID-only REMOVE와 GetPlanningScene 사후 조건을 적용한다 — 소유pick_target가 attached에서 사라지고 world에 정확히 하나 존재하는지 검증하며, 물리 release 후 새 원본 RGB-D 중심으로 world 형상을 만든다 — 이전 명령상 receiver 중심과 실제 배치 중심의 차이를 무시하면 retreat 충돌 검사가 잘못될 수 있다. 물리 목적지·full Cartesian fraction·관측 수명·접촉 기준은 완화하지 않는다.

새 placed_scene API 부재 RED 후 관련3 PASS. 별도domain136의 실제 설치 MoveIt API probe도 PASS: 잘못된 parent는 outer success=true/still attached=true 재현, ID-only 제거·관측 world 중심 readback·revision1 확인, shutdown ACK/exit0. 원래614e의191.942sim초 관측과 기록된 수명으로 검사했으며 live 권한이나 새 물리 실행이 아니다. 근거 offline_detach_api_v11.json. 연속 동작은 새 소스 동결 후 별도로 검증한다.

새 후보317 PASS/48.11초, build14.3초·설치59모듈/94자산/venv child 감사 PASS. v11 source338/assets94 SHA256 db5586b32b1e4947d0dc3026cc2f35b2e8c1fac7bc39c6052ab71cb1f9f92389. 공개 staging으로 native 사본과 공유 lock realpath 확인. v10 두 사례 원본·source archive를 유지하고 각각4,433,937/46,324,913byte raw archive 생성. 다음 실제 UUID 408dabfc-fca3-44e9-8087-fafb3984dd14. 새 물리 인수는 아직 대기.

### 2026-11-05 재개: 반복 지연을 근거별로 분해

v11 UUID408dabfc-fca3-44e9-8087-fafb3984dd14는 이동 초기에 VISION_EXPIRED로 전체 FAIL. trial4.878sim초/26.334wall초·CPU52.347%·tilt0.031468rad·bag close/12 child 정상 회수/worker join/잔여0/lock free. source338을 실제 native 사본에서 source_v11/runtime_source.tar.gz로 전수 hash 보존(SHA7d9379e25f7114808e43cdf962e342e99437cb6a3c939c1ddb9e6a3d651d8515). 분리 수정의 물리 평가 구간에는 도달하지 않았다.

fault decision284.319901497wall에서 마지막 health의 capture284.016571911wall은303.330ms 나이였다. 그 frame의 render 완료는284.157893wall(141.321ms), publish 종료284.159183wall, health validation284.182517wall. 다음 capture284.176819wall은 render284.293698wall(116.879ms), publish284.295161wall, validation284.324161wall로 fault보다4.259ms 늦었다. 이후 수신된 fresh frame을 과거 판정에 소급 적용하지 않는다. 이 사례는 v4의 혼합 FIFO 지연과 구분하며 원본300ms 기준을 유지한다.

공식 Jazzy executor/콜백 그룹 문서와rclpy GitHub #1223을 조회했다. 기본 callback group은 mutually exclusive이며 단순 MultiThreadedExecutor 교체는 독립 실행을 보증하지 않는다. #1223은 Iron/FastDDS의 제보로 이 Jazzy 로봇의 동일 원인 증거가 아니다. 무조건 executor/QoS 교체 대신 현재 source→render→publish→native receipt→validation 경계를 측정한다.

종료 후 실제 저장20자세를100frame 다시 렌더했다(새 physics/ROS/명령 없음). 실제 graphics는Mesa25.2.8-0ubuntu0.24.04.4·llvmpipe LLVM20.1.2이며 EGL을 쓴다고 하드웨어 GPU라고 부르지 않는다. warmup5개 제외95frame의 forward median0.129ms/update0.039ms/render4.758ms(p95 8.325ms/max27.471ms). 따라서141ms를 고정 모델 렌더 비용으로 단정할 수 없다. idle benchmark로 부하 중 deadline을 보증하지 않는다. 실제 작업 cgroup/non-systemd cpu.max는max100000, throttled0이며 조회 시점 pressure0이다. 과거 실행 중 부하 상태는 이 값만으로 판단하지 않는다.

Ruling: 다음 실행은 제어/기하/임계값을 바꾸지 않고 render 시작·완료·process CPU와 소유 프로세스별 CPU를 계측한다 — queue 대기와 실제 계산/스케줄 지연을 분리하지 않고 렌더 옵션이나 스레드 수를 바꾸면 추측성 수정이 된다 — 한 번의 diagnostic 실행 비용을 허용하고 원인을 특정한다. source capture 시각은 유지한다. renderer 계측 RED1/PASS1 후 GREEN3(PASS5.22초,314 deselected). 전체317개 중 변경 영향의 작은 실제 renderer/CPU 시험만 재확인했으며 전체 재실행으로 표현하지 않는다.

v12 계측 후보: build15.6초·설치59모듈/94자산/actual child PASS. source338/assets94 SHA256 a4aa2be7819fd36fc12abd4f4c7e793ad11c80c1dc0cc79fbfda514f045abfda. 새 native staging·공유 lock/잔여 확인 PASS. 다음 actual diagnostic UUID b0ccbf5f-0c95-4325-bf7f-a71338dc5cd0. 제어/물리/한도 변경 없음.

v12 actual UUIDb0ccbf5f-0c95-4325-bf7f-a71338dc5cd0는 초기 navigation/정착/find를 통과했으나 첫 arm warmup goal이 거부돼 전체 FAIL. engine fault는MISSION_EXPIRED. 원본 heartbeat sequence1 send10850.281082→sequence2 send10850.736212로455ms 간격이며 수신/relay가 아니라 producer 갱신 자체가 끊겼다. 첫 action 전이므로 팔 궤적 실패로 분류하지 않는다. trial10.842sim초/34.862797wall초·CPU47.583%·tilt0.035406rad·bag close/12 child clean exit/worker join/lock free.

첫 action 준비는 live lease READY 후run_arm_probe lazy import·ActionClient 생성·타입 지원 최초 로딩을 동기 수행한다. 설치rclpy7.1.12의 action/client.py와type_support.py는ActionClient 생성 시 아직 없는 타입 지원을 동기로 import하는 경계를 확인했다. 별도domain136 실제 콜드 probe(명령0)는warmup import16.635ms/첫arm client98.471ms/gripper1.519ms/goal구성0.195ms. 이 idle값이 live455ms 전부를 증명하지는 않지만, owner가 갱신할 수 없는 초기화 구간이 live 권한 안에 있다는 구조적 결함은 확인된다.

Ruling: 13.8 ValidationSession.ready에서 warmup 모듈과 실제 action3종/MoveIt service4종 타입 지원을 미리 준비한다 — 공식 ROS lifecycle의 configure 단계에서 일회 준비를 끝내고 active 단계의 긴 초기화를 피하는 패턴을 참고한다 — 실제 ROS client 생성/goal·result·cancel 소유권은 기존 한 owner와DeferredClients에 그대로 둔다. base13.7 실행 경로에는 적용하지 않는다. preload는새 권한/heartbeat가 아니며 live lease 시작을 늦춰서 오래된 관측을 허용하지 않는다.

독립 prepared probe는동작 전 준비340.085ms 후warmup import0.002ms/arm client5.420ms/gripper1.380ms였다. 준비비용이 사라진 것이 아니라 live 권한 이전으로 이동한 결과다. 실제 warmup client 구간도 별도 timing으로 기록하여 가설을 다시 확인한다. 신규API 부재 RED 후 시험 driver의script 검색 경로 누락1 FAIL을 명시적으로 수정했다. 새 전체 회귀와 실제 연속 재검증은 대기다.

v13 전체318 PASS/51.06초. build·설치60모듈/94자산/child PASS, source340/assets94 SHA256 6bb216f5f04859218d03e59fd84414cf1e976383dc204f33cddaf82afc81a732. native 사본·동일 공유 lock/잔여 확인 PASS. 다음 actual UUID 22d69f96-a916-4652-98e5-8f0fd461e2d1. rclpy 공식7.1.12 tag의action/client.py와type_support.py도 GitHub connector로 읽어 설치 버전과 맞췄다.

### v13 실제 결과와 검출 구조 재검토

v13 UUID22d69f96-a916-4652-98e5-8f0fd461e2d1는최초arm 준비/여러 실제warmup action을통과했지만GRASP_APPROACH 중 OBSERVATION_EXPIRED로 전체 FAIL. accepted3155/rejected6(모두surface fit). trial105.88sim초/247.167572wall초·CPU44.764%·tilt0.034285rad·bag close/12 child clean exit/worker join/잔여0/lock free. 초기화 수정은 실제 첫 client15.922ms/11.856ms로 이전 실패 지점을 통과했지만 전체 강건성 증거는 아니다.

종료 후 마지막 raw frame을 분해했다. 기존3x3 foreground boundary 처리에서는제거0pixel. 상하component223/194pixel·centroid차1.259mm·높이79.393mm로 결합 가능. robust중심(1.800023,-0.000111)m인데전체sideRMS1.578mm/q90 0.0998mm였다. 실제표면대부분의반경은19.85~19.94mm이나 소수점은33.590mm다. v9와같은소수깊이outlier계열이남았으므로카메라마운트나이웃threshold를더조정하지않고표면합의점모델을재검토했다.

Ruling: PCL공식cylinder segmentation의모델/합의점선별/계수재계산패턴을채택한다 — 기존SciPy soft_l1중심추정은소수outlier의영향을줄이지만그뒤모든점을한평균RMS로거부하여robust추정효과를상쇄했다 — 알려진upright축/반경의작은문제로제한하며PCL의자유축RANSAC/normal추정/일반객체인식으로확대하지않는다. 새mode만95%이상side점이기존q90경계와같은2mm이내일때inlier를재계산하고RMS1.5mm/높이75~105%/최소20점/side폭을검사한다. rawRMS/전체점/inlier비율/제거수/새측정정의를metadata로명시한다. 이는RMS의모집단을바꾸는명시적검출계약변경이며단순문서보완이라고부르지않는다.

13.8 carry opt-in은robust_consensus=True·filter_boundary=False로전환한다. 이전이웃pixel처리를누적하지않는다. 기본13.6/13.7은둘다False로유지한다. 원본capture/TF/GID/hash와물리/권한/안전기준은유지한다. 새v13 rawRGB-D를고정fixture로보존했다. API부재3 RED 후최초후보7 PASS/1 FAIL은고정120행crop이실제캔의상반부를지우지못한시험데이터오류였다. 실제red bounding box의중간행기준으로고쳤고v9원본도새mode회귀에추가했다. 전체회귀와새물리실행은대기다.

v14 후보322 PASS/54.67초, 설치60모듈/94자산/child PASS. source344/assets94 SHA256 e03942989bd3ab60d160f29ea4e6b665046dec00ca1f8fb45e9f20ec86ade5be. native staging/공유 lock/잔여 PASS. v13 exact source340 보존 SHA b2b97ee3c94a723abf7cb0c05bbd3276bc0317bbe0fcd2b14a50529379efae7b. v11/v12/v13 FAIL을3.895/5.120/27.911MB raw archive로 보존하고 원본도 유지했다. 다음 actual UUID 60ecc5f5-8385-44d5-83ec-ecd829af8b3b.

### v14: 실제 파지/검출 통과 뒤 advisory 파일 오류로 취소

v14 UUID60ecc5f5-8385-44d5-83ec-ecd829af8b3b는파지PASS(최소100.460mm/2.18sim초/접촉100%/slip0.02731mm) 후귀환중전체FAIL했다. trial160.6sim초/349.706125wall초·CPU45.622%. 시작 시점부터의 live_status는참고치이며실제최종상태는trial/BT/engine으로판독했다.12 child clean exit/worker join/공유 lock free. 이전표면검출실패구간을통과했으나전체미션성공은아니다.

최초원인은로봇/비전fault가아니라BT timer의live_status.tmp→live_status.json replace PermissionError(Errno13)다. Windows측상태조회와WSL측파일교체가충돌했고, advisory파일예외가BT executor로전파되어mission_exception 취소를발생시켰다. RETURN_GOAL_FAILED는그취소의후속현상이다. Microsoft CreateFileW의FILE_SHARE_DELETE 설명은rename에도delete공유가필요함을명시하며WSL #3395도Windows watcher/rename EACCES의비교사례다.

새빈시험폴더에서Windows FileStream을FileShare.ReadWrite(DELETE 공유없음)로열어WSL replace를실제로재현했다. 새writer의동작은PermissionError1회기록·기존JSON보존·정상join PASS였다. 단순추정으로Windows 권한설정/프로세스를변경하지않는다. 관련Python3.12 queue/Thread와공식ROS의blocking I/O 분리원칙을참고했다.

Ruling: live_status의파일I/O를ROS timer에서owned latest-only writer thread로분리한다 — 상태표시는새권한이나최종판정이아니므로OS reader lock을로봇취소로전파하면안된다 — pending은한개로제한하고느린기록은다음상태로대체하며오류/대체수/마지막오류/실제join을telemetry_delivery.json에남긴다. shutdown후join미확인은정상성공으로바꾸지않는다. 실제제어/BT goal·관측/접촉/취소계약은변경하지않는다. API부재RED 후잠금복구·blocked writer 누적제한·join실패표시·정상atomic최종전달3 PASS/1.85초. 실제Windows deny-delete/WSL probe도PASS. 전체회귀/새실제실행은대기다.

v15 후보325 PASS/48.99초. 설치61모듈/94자산/actual child PASS. source346/assets94 SHA256 05e33c7a6703f2d105d577be240a0dca60d2924cd3e464d940a5f9ea90a4aa74. native staging·공유 lock/잔여 PASS. v14 exact source344 보존 SHA2f1e401ac266e3604b1b9655be5112c56526b88381898088b3cd6689ac675827, raw40,779,702byte SHA4af8b4183642dfa90d1c30ff3133a635804a96595c83c5e9b94aa24ff2f91c39. 다음 actual UUID fcf0dbe0-de70-4ca1-a86e-66133a62d2f8. 동작과 무관한Windows advisory reader lock을3초간주입해예외전파차단도확인할예정이며고정설정10회평가와구분한다.

### v15 동일 engine 연속 임무 최종 PASS

UUIDfcf0dbe0-de70-4ca1-a86e-66133a62d2f8, source v15/346·assets94, SHA25605e33c7a6703f2d105d577be240a0dca60d2924cd3e464d940a5f9ea90a4aa74. 최종trial.success=true/complete=true, BT mission terminalSUCCESS·worker exit0/join, 소유goal14개SUCCEEDED/pending0/errors없음, 자식12개clean exit·잔여0/launch0·공유lock free. 같은engine에서파지→운반→정착→LOWER→실측개방→관측기반충돌모델분리→full Cartesian retreat→유지→REVOKED→Finish를완료했다. 모든Cartesian fraction1.0/error1, detach readback에서attached_removed=true/worldcenter(-0.801368,0.006537,0.539961)m.

파지minimum100.27058mm/max102.94071mm/2.18sim초hold/양finger접촉100%/slip0.027308mm PASS. 운반거리2.5484349m·접촉100%·높이/수령위치/높이/지지/개방/2sim초이상post-release hold의8항목모두true. 물리pick/transport둘다PASS. 선택12토픽bag정상close. 이는개발fixture한사례이며원고Level1/2/3나10회강건성완료가아니다.

임무210.484sim초/492.118861wall초, 귀환오차최종trial기준0.05016494m, tilt0.03946457rad, CPU46.97787%(8 affinity cores 정규화). 120초/3cm목표는미달이며그대로남긴다. 수행중status의약4.6cm와최종return snapshot의5.02cm를혼용하지않는다.

이사례에는Windows reader의DELETE미공유잠금을상태파일에3.115초주입했다. telemetry_delivery는published527/write_errors3/overwritten0/joinedtrue이고3회모두PermissionError다. 이후표시가정상복구됐고미션취소로전파되지않았다. 순수무주입반복평가로표현하지않는다. 과거v14FAULT도삭제하지않는다. 공식패턴의사전타입준비·모델합의점·MoveIt분리postcondition·비제어상태기록분리를합친필수단일연속사례가처음통과했다.

다음월드M0: floor position-only IK에서는0.5~0.7m stand-off 후보를얻었다. 최초full-pose service probe의-21은TF 설정누락이며도달불가능증거가아니다. 원래v1오류자료를보존하고명시적offline 고정odom→base TF로재확인한다. engine/actuator는실행하지않는다. 위치목표미달은기존Nav2 xy_goal_tolerance0.06 설정과공식1.3.13 SimpleGoalChecker를조사했으며아직13.8정밀도수정이나실제인수로표현하지않는다.

v15 사후보존: 실제닫힌bag12토픽/164399메시지무결성PASS. exact native source346개 전수hash보존archive SHA9318dca2a8a37add3d485ae05e20cc27e7db175379642eb466dad67fbbb6292d. 모델제외raw58,135,258byte SHAd42dd09a8dc57adf95b7529f58699fb0f81895778a358c1dca4e2fea34cf752b. 새빈native폴더에41파일hash복원PASS, 원래trial/BT/nav/source hash동일·success=true보존. 실제재실행이나원격다운로드검증은아니다. Task2의최소연속기능인수/증거보존을완료하고원고월드와10회는Task4에남긴다.

바닥월드full-pose M0에서v1의TF누락과v3의양성대조군선정실패를분리했다. v3는floor경사접근후보의실제IK해가있어도table sign+ 대조군이안풀려API_SETUP_FAILURE로보수판정했다. 공식MoveIt2.12.4 kinematics_service_capability.cpp는timeout.sec만setFromIK에전달한다. v4는정수1초·양쪽roll대조군·선택floor후보와독립URDF FK잔차검사를사용했다. table sign- 대조군PASS 및floor stand-off0.55m/pitch45°·0.60/0.65m pitch30°/sign-의pre-grasp/grasp 모두실제TRAC-IK 해를얻었다. position<2mm/orientation<0.02rad FK확인·shutdownACK/exit0. avoid_collisions=false의정적workspace검사이며물리·충돌경로·시야성공은아니다. 새body고정/WBC나학습은추가하지않았다.

### Task4A: 원고 Level1의명시적연결

원고floor2m를development와구분하는불변scenario를추가했다. level1_floor는target(2,0,0.04), 수령(-0.6,0,0.04), 고정camera(0.4,0.4,0.29)/yaw-40/pitch down35도, stand-off0.60m/pitch down30도/pre0.06m다. scenario.json과trial의scenario/name/hash/level로출처를남긴다. 기존development 기본값·기존프로필은유지하며알수없는ID는시작전에거부한다.

원래floor그대로target실제접촉힘을측정한다. 가짜중복receiving patch를추가하지않았다. 개방권한에는측정지지힘과lease의새관측수령영역을같이요구하며관측의기존수명/소유권검사를유지한다. 정적M0에서팔이몸통을관통하는IK해를발견했으므로floor모드의실측arm-vs-body/leg/floor 관통접촉힘이0.005N를넘으면FLOOR_ARM_CONTACT로latch한다. target freejoint를제어입력으로쓰지않는다. 양성실제MuJoCo관통fixture가fault를내는시험과바닥지지측정/잘못된수령점거부를확인했다.

내려놓기는원본관측baseline과scenario 높이차를쓰며floor후퇴는접근축반대방향으로8cm 올라온다. 기존개발fixture의world+x 수평후퇴는유지한다. 기존Planner와ownedNativeAction/lease/취소회수를재사용하고보행루프를복제하지않는다. source중2개기존파일의 -text/CRLF 형식을유지하며일회git whitespace검사에cr-at-eol을명시했다. 전역설정변경은없다.

새 API RED와geometry/support/force/판정 GREEN 후전체334 PASS/53.06초. 추가로실제초기/사전/파지3자세를한시험으로확인해1 PASS/2.88초(334 deselected). 이를335개전체를한번에실행했다고쓰지않는다. M0 nominal baseZ0.29에서도d0.60/pitch30/pre0.06은3자세시야와관통없음을확인했으나중간경로/물리인수는별도다.

v16 build/설치/actual child 감사 PASS, source350/assets94 SHA256 061bb5a92b75de075c83b35227538c53e034d25735b7ba8a548b70aec56a5203. native staging/shared lock/잔여PASS. 다음 actual 원고Level1 UUID 8fb61073-d484-43d8-a2d3-3aa51c7c7572. v15 development SUCCESS와다른fixture·별도증거다.

### v16 실제 FAIL과 v17 센서 보조 표시 원인 수정

v16 UUID8fb61073-d484-43d8-a2d3-3aa51c7c7572는navigation/정착/find/사전파지를통과했지만GRASP_APPROACH의surface consensus 거부59회로OBSERVATION_EXPIRED FAIL. accepted3450,126.44sim초/274.480495wall초,CPU43.609%,tilt0.0363422rad. CLOSE/파지성공은없고floor contact fault도없다.12 child clean exit/worker join/lock free. 원본실패를보존한다.

종료후rawRGB-D/실제qpos 재렌더링은99.9896% RGB동일·depth최대3.1µm차·TF오차8.88e-16, native depth 문제pixel차0이었다. side190점중41점은모두segmentation ID1/type6으로실제물리geom이아닌붉은attachment_site였다. 최초첫채널만geom으로읽은벽이름진단은오류이며두채널objectID/type으로정정했다. 이ID는사후진단전용이며제어입력에추가하지않는다. geom불투명강제는효과없고sitegroup만off한동일장면은합의100%·중심(2.0000523,-0.0000591,0.0403589)m·높이78.998mm로기존기준통과.

Ruling: 공식MuJoCo3.13.0 mjvisualize.h/engine_vis_visualize.c의별도sitegroup패턴으로latest paired센서stream의site만제외한다 — 물리표면이아닌좌표표시가RGB-D검출에섞이는센서설정결함이다 — legacy카메라/외부모델/물리/검출95%·2mm/관측수명/권한을그대로유지하며새world전체성공을주장하지않는다. 자세한공식ref·분석·한계는SECTION_13_8_FLOOR_VISION_DIAGNOSIS_KO.md에기록했다.

실제실패qpos고정fixture와기존옵션실패/새옵션성공쌍시험: API부재1 RED→1 PASS/2.59초(335 deselected). 실제sensor옵션으로기존카메라시험도연결한전체336 PASS/55.03초. v16 exact source350 hash보존archive SHAd87852468a494a093adeadf23f5f3e89b4f3b5f325335db0391dc9051eedc096. raw31,735,062byte SHAcedc0417234dd9a4d186cf2086394f2f107fc458e839a5526a96baf8c8fa25a3. 원본유지. 새build/설치/동결과새실제Level1은별도진행한다.
v17 build12.7초·설치62모듈/기존navigation34/manipulation24/BT6·94자산/실제venv child감사PASS. source351/assets94 SHA256fadf346d87273f9efb59efcd27234cdbdc5f99bb93063097d1b86a4b540b2390. exact native source복사/동일실제공유lock/잔여없음PASS. 실제Level1 새UUID65199d33-38ee-4073-a561-bb8b22b5e79c를실행한다. 제어·물리·원본capture/TF·95%검출기준은v16과같고sensor site표시만수정했다.
### v17 실제: 비전 수정 통과·바닥 지지 대기 FAIL

UUID65199d33-38ee-4073-a561-bb8b22b5e79c, actualLevel1. vision6134 accepted/거부0/fault없음. 최소103.9716mm lift·2.2sim초hold·양접촉100%·slip0.027672mm로pickPASS. 귀환actual오차43.3379mm. LOWER의fullCartesian계획/실제actionSUCCEEDED뒤5wall초내지지가확인되지않아전체FAIL. RELEASE는없다. trial200.394sim초/478.197393wall초·CPU44.46431%·tilt0.045418rad,소유goal12개SUCCEEDED/pending0/errors없음·workerjoin·12childcleanexit·lockfree. 과거site관측실패는이번전체접근에서재발하지않았으나미션전체성공은아니다.

종료후동일시간축비교: LOWER arm terminalwall17857.002467/sim199.44때물체centerZ0.041788626m·최대팔속도0.001856rad/s. 최초실측support0.01492N은sim201.882/wall17862.127034로terminal보다5.124567wall초/2.442sim초뒤다. 정리중늦게발생한접촉을정상놓기성공으로승격하지않는다. nativeaction은위치오차0.05rad/속도0.05rad/s·유지조건의관절목표도달이며지지접촉보증이아니다. Cartesian fraction1도지지보증이아니다. 마지막계획의FK잔차4.159mm는별도기록하며이숫자만을실측수직간격으로해석하지않는다.

공식control_msgs FollowJointTrajectory.action의관절goal_tolerance 계약과기존run_pick의실측정착gate를참고한다. Ruling: floor LOWER뒤에는기존관측/lease와접촉경계를유지하면서팔실측속도<=0.003rad/s·base정착·support>0.01N을0.5sim초연속확인한다 — action완료후물체접촉상태를검증해야하며고정5wall초만기다려정착을가정할수없다 — 이floor정착단계의상한은기존pick정착과같은20wall초로명시적으로늘린다. 기본development의동작/기한은유지한다. action120sim/240wall·mission600sim·capture300ms/TF100ms는변경하지않고지지없는시간만으로개방하지않는다. 새실제검증은필요하다.
v18 후보: place_settling API부재collection RED 뒤8 PASS/1.90초. 최초전체344 PASS/53.74초후READY/PLACE명시적guard를추가했고최종source로관련8 PASS/1.89초(336 deselected)를재확인했다. 344개전체를그최종guard추가후다시실행했다고쓰지않는다. 이추가guard의실제연결은새actual실행에서확인한다. floor정착은속도/지지상실/NaN/결측/역행clock에서hold를리셋한다. v17정확소스archive SHAf15af2529444c14593113ae3049b76ee21b3fb927551cedde62fd34d3c4d08c7, raw51,384,145byte SHA39aac6e2683db89d6aa08d1702907f3766e3f95a97aeb638a79c872667a874ef보존. 공식action정의는실제설치control_msgs5.10.0으로재확인했다(첫참고4.8.0과구분). 로컬fee04cd1에센서site수정/336시험/v16·v17실패근거를선택commit했고push는없다.
v18 build13.6초·설치63모듈/94자산/actualchild PASS,source353/assets94 SHA256b45fa5aebf8cb60dbba444e3dca5bd9fd258b811d0dfbfa6f513129c4b2c6101. exactnative복사/동일공유lock/잔여없음PASS. 새actualLevel1 UUIDcb260b36-8fae-46e9-97c8-927376588f46. Nav2정밀도는아직기존0.06m이며이실행에새튜닝을누적하지않는다.
### v18: 바닥 지지 보완은 미도달, 실제 작은 가림 조각의 조기 폐기

UUIDcb260b36-8fae-46e9-97c8-927376588f46는GRASP_APPROACH에서OBSERVATION_EXPIRED FAIL. vision3748 accepted/70 rejected(높이가시성)/vision fault없음.130.392sim초/296.650778wall초,CPU43.8524%,tilt0.063353rad. CLOSE/지지정착단계에미도달했으므로v18정착수정의실제효과를판정하지않는다. 원래FAIL·source353/archive SHAa963904734f6ed47b1db1e9c8af046dc1202c0f24437581a217d70ed9d619e90/raw33,515,948byte SHA41b1ee23dad4ae37cf33450b91489345758a86ccd252570595eb4a8735a1acd0 보존. worker/12child회수·공유lockfree.

실제마지막RGB-D는물체tilt0/양finger접촉0/합의100%/sideRMS0.0405mm다. site오염은재발하지않았다. 붉은상부245pixel(높이37.18~79.86mm)과하부13pixel(2.96~17.37mm),centroid차13.53mm로같은반경20mm모델에맞는다. 두조각전체는기존height76.306mm/중심(2.0000515,-0.0000821,0.041705)m로검출성공한다. 그러나기존연결성분별20pixel필터가하부13pixel을모델결합전에버렸다. 아래조각이없으면기존75%가시높이를확인할수없다.

구조재검토: 카메라위치를실패장면마다움직이거나전체높이/합의threshold를낮추는안은채택하지않는다. 2D연결조각을물체후보와동일시하는earlyfilter가문제다. 공식PCL1.15.1 cylinder_segmentation.cpp는필터된전체3Dcloud에모델을추정하고inlier를선별하며,가려진image patch마다독립적인물체최소크기를요구하지않는다. 자유축PCL알고리즘/5cm허용오차는가져오지않는다.

Ruling: robust mode에한해20pixel이상anchor에가까운작은axialfragment를남겨기존3D전체모델을검증한다 — 20점최소조건은합쳐진실제side모델에계속적용하고작은조각은단독후보가될수없다 — legacy필터/95%합의/2mm/높이75~105%/side폭/최소20점은유지한다. 무관fragment·단독small·아래가시영역삭제시험을추가하고저장된actual접근궤적을조밀하게재현한뒤새actual을진행한다. 이는후보결합계약의명시적변경이며과거실패를성공으로재판정하지않는다.
v19조각검증: 최초3 FAIL중음성시험1개는R채널만사용해회색까지마스크에넣은시험오류였다. 실제red dominance조건으로정정후2 FAIL/1 PASS를확인했다. anchor20pixel이상+작은auxiliary보존/동일기하모델검사수정후3 PASS/2.01초. 실제v17/v18 GRASP_APPROACH의234자세를100sim ms간격고정해재렌더링한회귀1 PASS/7.71초(347 deselected). source정답좌표는추정후평가전용이다. 모든실제그리퍼관측을실시간재생한것이나새물리성공으로부르지않는다. 전체회귀실행중이며이후소스동결전까지제어코드는추가변경하지않는다.
v19최초전체는347 PASS/1 FAIL(81.39초),실제publisher교체시험이교체주입전arm준비에서FUTURE_SOURCE:joints로실패했다. 독립WireTests군도23 PASS/1 FAIL(23.91초),이번에는base손실주입전같은시작실패였다. gateway/수명/clock기준을늘리지않고기존StartupTrace를시험전용으로연결한시험파일진단은실제11개중10 PASS/1 FAIL(10.62초)이었다. diagnostic의gateway_8은최초native수신묶음의clock2.34초/raw2.40초/joints2.44초와더미래base를기록했다. 수신wall은32584.917초근처로모였고첫처리clock보다100ms이상미래인state가들어와정상거부했다. 단순callback순서추측으로productionguard를고치지않는다.

Ruling: test_ros_wire의합성producer는native relay의2 clock/1 base/1 joints/1 raw subscription과gateway relay publisher1개가매칭되기전에는합성시각을진행하거나sample을발행하지않는다 — 이시험들의목표는arm뒤입력손실/owner교체이며발견전서로다른시점의latest cache를만드는준비경쟁은혼입요인이다 — readiness는한번만latch하여이후의손실/교체주입을차단하지않고원래3초arm준비예산과모든안전기준을유지한다. 공식rclpy7.1.12 Publisher.get_subscription_count와Jazzy executor의다른entity간FIFO보장없음설명을참고했다. 실제engine의모든startup실패를해결했다는뜻은아니다. 새24개wire군과전체회귀결과를별도로기록한다.
합성producer discovery gate후WireTests 24 PASS/23.00초(324 deselected). 그최종소스로전체348 PASS/57.79초. 이전347/1·23/1·진단10/1 실패로그를그대로보존하고전체PASS로덮어쓰지않는다. 상세원본수신자료와공식API/계약은SECTION_13_8_WIRE_STARTUP_DIAGNOSIS_KO.md. v19 build/설치63모듈·94자산·actualchild/source357/assets94 감사PASS,동결SHA256d1dd075ba4791e56caa13da8a8c2099fbdb620e93213df5e9b0229daf2f4fd97. 중단시build/staging은이미정상완료됐고engine은미실행이었다. 재개후로그와공유lock/소스사본을다시확인한다.
재개후348시험source snapshot과v19 freeze의357개소스hash전수동일PASS. build후준비로그와native사본은중단사이유지됐지만WSL boot ID는8fc29544-15b5-4ae1-b4ca-7eeb6324307e로바뀌었다. 새BEFORE_NATIVE_ENGINE_V19에서소유잔여0/공유lockfree PASS를확인하고UUID853f2592-ea9e-4567-ac7f-4d4aeabb4475를실행했다. 이전boot의monotonic시각을이번실행시각과섞지않는다. local55aed7ba에조각모델/정착gate/시험discovery준비/348시험과v18FAIL을선택commit했고push는없다.
### v19 실제: 관측 거부0, PRE_GRASP 개별action wall deadline

UUID853f2592-ea9e-4567-ac7f-4d4aeabb4475는비전3908 accepted/거부0/fault없음이었으나PRE_GRASP가240wall초내끝나지않아FAIL. trial114.82sim초/304.832936wall초·CPU43.3362%·tilt0.033838rad. actualengine116.854sim/306.24wall. nativearm시작sim25.316/wall86.007541→cancel ACKwall326.117113→ABORTED wall329.169920 reasonwall_deadline. 그뒤worker종료중MISSION_EXPIRED가관측됐으므로이차현상을최초heartbeat원인으로오인하지않는다. worker/12child회수·lockfree. source357 archive SHAe610241456c39c4753ff9073b4fd94d9ae0aee20727ed0736f8d310cc7357a0b/raw31,709,339byte SHA58905e87f110cc17fe1d425fbd1a95eb97908ae7429f135265023ea901c8e230보존. CLOSE/지지정착에미도달했다.

저장된plan2개는기존coarse시간배율1.25에서98.516/93.728sim초였다. 원래1.0배율이실패한이유는연속quintic의가속도0.104398/0.109915rad/s²가0.1을넘어서다. 같은Trajectory.from_points연속proof로feasible배율을구간탐색하고1%여유를더하면1.08274/1.05909배율,85.334/79.413sim초로줄며모든위치·속도0.05·가속도0.1·경계hold조건이그대로통과한다. 계산결과는pregrasp_timing_analysis_v19.json에보존했으며아직새물리성공이아니다.

Ruling: floor13.8 opt-in만기존coarsefeasible구간안에서12회bounded구간탐색후1%여유와같은연속proof를다시통과시킨시간배율을사용한다 — 기존25%단위배율선택은연속제약에필요한약5~7%보다불필요한시간을더했다 — waypoint/경로형상·PD·정책·0.05/0.1한계·120sim/240wallaction·600simmission·관측수명은유지한다. legacy/development기본coarse정책은보존한다. 공식MoveIt2.12.4 TOTG의속도/가속도제한시간화와ros2_control Jazzy의quintic연속성/overshoot설명을참고하되실제제어기는기존customnative다. 단순timeout연장이나새trajectory교체/동시goal로회피하지않는다.
시간보정회귀는첫-k선택에서주음성1 FAIL/기존1 PASS였고,양성함수이름을선택어와맞춰API부재2 FAIL/기존1 PASS를확인했다. bounded구간탐색옵션추가후새실제751점경로/미분환산/잘못된위치거부와기존TOTG를함께5 PASS/4.34초(345 deselected). 기본API는coarse이며floor13.8만refine_execution_scale=True를주입한다. 초기화·계산은기존ownedcomputeworker와poll을사용하고새nestedspin/동시goal은없다. 전체회귀를실행중이며이후소스는추가변경하지않는다. 공식ref/원본수치/한계는SECTION_13_8_TIMING_DIAGNOSIS_KO.md.
v20최초전체348 PASS/2 FAIL(57.62초). 두실패는기존test_candidate_timing의Planner.__new__ fixture가새constructor옵션을설정하지않은AttributeError다. 실제constructor는기본False를설정한다. fake에도False를명시하고전체최종회귀를다시확인한다. production기준이나검증기를수정해실패를숨기지않는다. 아직350전체PASS라고쓰지않는다.
fixture초기화보완후최종350 PASS/53.98초. 새로운production source를추가변경하지않고v20 build/설치/동결을진행한다. 최초348 PASS/2 FAIL도보존한다. 새actual은별도UUID/실행소스동결/공유lock으로검증하며이unit결과만으로walldeadline해결이나물리놓기성공을주장하지않는다.
v20 build16.6초/설치63모듈·94자산·actualchild PASS. source359/assets94 SHA2563c0d9de00c27ab52f6612e24b7c8e4bae46539099e3d8f6557e3d74c49ead006. 350시험source와실행동결359개전수동일PASS. native source/공유lock/소유잔여없는새boot확인PASS.

local28d17dec에v20시간보정/350시험·v19FAIL보존/보고서를선택commit했다. 새actualUUIDf4dd835b-09b0-4aed-b7ff-9a86b0eebcfb, native92c1c8a5244047acafe5391e07f5e5da. 새boot8e1bcbe0-655e-40d5-9e9e-f6e2e4db4003에서소유잔여0/공유lockfree를확인하고실행했다. Nav2정밀도는여전히기존0.06m이며새튜닝을누적하지않았다. 실제임무의성공과3cm/120초목표는별도로판정한다.

### v20 actual: 시간보정활성확인, 드문원본capture지연으로FAIL

UUIDf4dd835b-09b0-4aed-b7ff-9a86b0eebcfb,trial61.686sim/158.594726wall초·CPU42.3786%·tilt0.031605rad. PRE_GRASP중OBSERVATION_EXPIRED FAIL,vision2031 accepted/거부1(capture/clock/TF expired)·형상거부0·visionfault없음. 새timeadapter policy continuous_bracket_1pct_margin/scale1.06295349·선택plan79.656225sim초가실제적용됐으나완료전에관측fault로중단됐으므로240wall완료를입증하지못했다. 접촉fault없음·worker/12child회수·lockfree.

첫faultwall181.029897/sim61.820, engine이사용한관측capture61.814sim의원본wall180.701058은328.839ms나이였다. 그frame의render시작180.866025/끝180.891282(25.257ms),대기+pre-offer포함164.967ms. sourcecapture61.816sim/wall180.872739의다음frame은inference180.997220에이미완료됐으나engine의observation channel최종처리는180.962708인상태에서fault가발생했다. camerahealthchannel은181.006100에새frame을처리했다. sourceage를receipt나now로치환하지않는다.

같은시점engine step_outlier는capture_sensor stage172.623ms/threadCPU87.604ms,GC사건없음이었다. 이stage는ray scan/TF publish/requestoffer등을묶으며요청은mp.Queue feeder를지나므로164.967ms를순수renderer계산이나순수queue대기라고단정할수없다. 다음은실제offer시각과scan/TF단계를작게분리계측하고저장상태의짧은부품probe로구분한다. 프로파일없이카메라위치·검출threshold·300ms수명이나OS우선순위를바꾸지않는다. 긴actual을추측수정으로반복하지않는다.
v21계측API부재2 FAIL/기존1 PASS→계측3 PASS/6.43초(348 deselected). 원본capturewall은보존하고request_offer_wall/요청→render시작을추가했다. SensorSuite scan/상태발행/put비용은최근256개deque와총수로만모으고close때파일을쓴다. 순서/동작/임계값변경은없다. Python3.12 공식Queue/CPython3.12.3 feeder소스를읽어put반환과worker수신을구분했다.

짧은domain136 부품재현: quiet producer22.294초/276frame/정상camera회수,pre-offer최대12.012ms/요청→시작최대1.237ms. 첫vision/relay연결은원래map→odom 정적TF를fixture에빠뜨려tf_samples0/accepted0이었으므로end-to-end API_SETUP_FAILURE로보존했다. TF를명시한v2는22.731초/277frame/vision221 accepted·거부0·fault없음/자식2개와camera정상회수,pre-offer최대11.315ms/요청→시작1.179ms였다.

원래12토픽목록의recorder와추가상태발행을붙인63.391초probe도830frame/vision731 accepted·거부0·fault없음/자식3개와camera정상회수였다. pre-offer최대11.059ms/요청→시작6.273ms/render8.707ms,최근256개stage통계다. 발행자가없는토픽은record대상설정만있으며원래실제12토픽mission bag완료로부르지않는다. 원래물리/정책/전체ROS부하는없어서165ms지연은여전히재현되지않았다. recorder단독원인이나해결완료로단정하지않고QoS/전역설정을바꾸지않는다.

Ruling: v21은제어변경없이카메라/센서단계계측만추가한진단source로freeze한다 — 부품에서재현되지않은전체부하의pre-offer/전달경계를실제한사례로분리해야한다 — 기본350검증control을유지하고변경영향camera/startup/IPC시험과실제부품probe를확인한다. metadata만을이유로전체350을다시반복하지않고관련선택결과를정확히기록한다. 기존native160f4eba6cee4271bd684ea26284a2af가현재계측source와같은hash인지는새freeze와전수비교한다. 긴기존matrix는반복하지않는다.
v21camera/startup/IPC선택은20 PASS/1 FAIL(20.65초),기존test_camera_cadence가SensorSuite.__new__로만들어latest_camera기본값이없었다. 실제free생성자는renderer/ROS부작용이없으므로두cadence시험을실제생성자로바꿔향후초기화누락을방지했다. 원래시각/cadence검증은그대로다. 최종동일선택시험이통과할때만prepare_v21을진행한다. production계측외제어변경은없다.
v21최종관련21 PASS/24.23초(330 deselected). source360/assets94 SHA256d17a2607042d4e324c064008715233df8eacd6989cb5a80ead9112dc2be94f65. 실제venvchild/설치63모듈·94자산/동일공유lock/소유잔여감사PASS. 21선택시험snapshot과실행동결360개소스hash전수일치PASS. 실제control350이력과계측21시험을구분한다.

### v21 실제 FAIL 보존과 v22 owner 진단

v21 UUIDe0b2d5b0-0678-41e0-87c6-c48793781402는190.252sim/457.378wall초에RETREAT 중MISSION_EXPIRED FAIL. 바닥pick PASS,2.560m운반/귀환/실제지지·개방·detach를확인했다. 귀환36.336mm·CPU43.886%·tilt0.045512rad. 운반carry_height는21.802mm하강으로20mm기준을초과해원본FAIL유지(나머지7개true). worker/12child회수·bagclose·lockfree다. 최신256개capturestage에서pre-offer최대41.321ms/put3.118ms이며전체6502개최대통계가아니다.

첫faultwall471.764171에서마지막heartbeat발행471.449932/즉시native수신471.450333였고다음발행471.814146까지364.214ms공백이다. 두stamp는189902000000ns로같다. owner생산지연이며engineGC자료만으로별도ownerGC를배제할수없다. 원인확정전300ms수명이나50ms주기·OS/GIL정책·소유스레드를바꾸지않는다.

Ruling: 저장status20,417개의원문문자열보관실험은RSS308764→199492KiB/추적객체236304→93391/수동gen2약64→17ms로줄었다 — 현재파싱된status만제어에사용하고과거journal은원문으로보관하는13.8opt-in을적용한다 — 실제364ms원인해결과동일시하지않으며같은owner에기존GCTiming관측을추가한다. CPython3.12.3 gc.rst callbacks/is_tracked 및rosbag2 0.26.11 serialized recorder패턴과차이는LATENCY_DIAGNOSIS에기록했다. GC정책/권한/원본시각은그대로다.

실제handoff수명시험2 FAIL/1 PASS(3.49초)→관련4 PASS/3.41초. 예외회수/prettyJSON/legacy까지추가한전체최종357 PASS/61.30초. 시험native component_source_d5518f38026c4349a1320136d15f3bd3. 원래v21 FAIL과archive/hash·실험원본을보존했다. 아직v22실제성공이아니다.
v22 build17.1초/설치63모듈·94자산·actualchild NumPy우선순위PASS. source361/assets94 SHA25656ebcc593888d49b3bbf77eeec59e23b33a0a3083ff271186f83ddb6cd0bc870. 전체357시험과동결361개전수hash일치. native live_source_fc8a33d4cf684a69b6afc210c57cc7a7와원래공유lockrealpath동일/실행전소유잔여0/lockfree를확인했다.

### v22 actual: 정상 연속 동작·종료, 원래 물리 기준 FAIL

local43917781 뒤UUIDab482f62-ea28-462d-a176-235c58573edb를source361/assets94동결로실행했다. BT SUCCESS, worker join/자식12개정상exit/engine정상종료/bagclose/lockfree다. 바닥pick104.458mm/hold2.2sim/접촉100% PASS→2.566m운반→귀환→지지정착→실제개방·detach→RETREAT→유지→Finish까지완료했다. trial199.538sim/490.767708wall초·runner513.623501wall초·귀환44.449mm·tilt0.0446295rad·CPU45.9498%. 3cm/120초목표미달.

물리transport는carry_height만false/나머지7true이며trial최종FAIL이다. 높이20.094314mm하강으로20mm기준을0.094314mm초과했다. 같은때TCP자체18.406087mm하강/상대이동3.977737mm,전체carry최대상대이동5.299600mm·환경지지힘최대0N이었다. 좌표계차이를별도carry_frame_analysis_v22.json으로보존하되기준이나원본판정을바꾸지않는다.

실제heartbeat9012회에서250/300ms초과공백0. 최대235.979593ms는GC와겹치지않았고마지막종료부근이다. gen2 GC2회65.110/63.029ms는각94.849/111.147ms발행간격과겹쳤다. 원문journal의부담은줄였지만실제gen2에는다른owner객체도포함된다. 이전364ms원인이나반복강건성해결로단정하지않는다. 프로세스소유/300ms계약/GC정책은유지했다. 초기사후분석shell의변수전달이빈경로가돼API실패했으며리터럴인자호출로수정,실제물리실패와구분했다.

sourcearchive SHA256ce8188ac386987553b97c1de820f2a5ec4b942c991b542e2e6f683671cfef9ef. raw56,066,134bytes/SHA256203fcbcf7d3b81abd46ecdd3f6348036092174b10b6fb0b048360b76e0de08ae,원본삭제없음. carry분석은archive생성이후생성한별도사후결과로보존한다. 다음은기존0.06mNav2허용반경과원고3cm목표의불일치를공식1.3.13구현에맞춰별도최소navigation사례로검증한다. 원래높이판정FAIL을숨기거나긴13.8전체사례를또반복하지않는다.
Ruling: 반복된3cm미달은기존Nav2 0.06m허용반경과목표불일치가확인됐다 — 공식1.3.13 SimpleGoalChecker를GitHub connector로재조회하고Level1 carry_v1 controller_server에만0.015m override를추가한다 — YAML기본/yaw/stateful/속도·정책과정착조건은유지한다. 되돌릴수있는3줄설정에구현을따라쓰는unit을추가하지않고실제parameter읽기+짧은navigation정식판정으로검증한다. 아직v23실제인수결과가아니다.

v23 navigation-only UUID93bcce10-caa5-4535-a31c-6c5e4a6ee0ee는실제GetParameters=0.06으로이동전PARAMETER_ADMISSION_FAILURE. 자식10개정상회수/lockfree. 이후terminal없는자료를원래정식verifier가읽어KeyError난도구실패도보존했다. 소스/설치launch hash7718e6649ddb7c0a694dbb2e1626d7e262913a0eaab47f379b48746007915bf1동일. 실제launchdict에는0.015가있었고ROSparser에서node-specific YAML뒤/**override를넣어도0.06이되는문제를엔진없이재현했다.

Ruling: 단순dictoverride는이설정범위에서실제적용되지않는다 — 공식Nav2 1.3.13 navigation_launch.py의ParameterFile/RewrittenYaml패턴과설치원본을읽고controller_server.ros__parameters.goal_checker.xy_goal_tolerance전체경로만재작성한다 — 원본YAML/legacy값은그대로이며실제ROSparser시험을추가한다. 최초1 FAIL/2 PASS(3.49초)→관련13 PASS/5.40초(347 deselected). nav2_common직접의존성을명시했고새글로벌설치는없다. v23실패freeze를수정하지않고v24새freeze로검증한다. 자세한근거는SECTION_13_8_NAVIGATION_PRECISION_DIAGNOSIS_KO.md.

v24 source362/assets94 SHA256ae5d7f4dbd5da8e6e619360071a580b3857a6669a7112f96497f17ae13cb30fa,build15.5초/설치63모듈과94자산감사PASS. 관련13시험과freeze362개전수hash일치PASS. 첫actual UUID6916dedd-6e65-403c-b8ba-180850a35b38는이동허가전FUTURE_SOURCE:base/ready_for_arm=false로시작실패했으며자식10개회수/lockfree. 제어/수명변경없이기존startup trace만켜같은동결의1회재현을확인했다.

두번째v24 actual UUID9e86b6f2-91e6-4a89-a6d9-a28b550ae40d 는controller실제xy0.015/yaw0.06/statefultrue를반환했다. unloaded forward(0.65,0,0) 정착11.822090mm/yaw0.000997rad/정식navigation PASS/precision PASS. 정지window0.710sim초/고유356sample,engine정상종료·자식10개정상회수·잔여0·lockfree다. 앞선startup실패원인해결이나반복강건성을주장하지않고,적재귀환π회전/Level1전체새실행은남아있다. 전체13.8완료나고정10회평가로확대하지않는다.
v23설정FAIL/v24시작FAIL/v24navigationPASS 세사례의정확한실행source와모델제외raw archive/hash를보존했다. v24공통sourcearchive00546a3806d65d1e817d58e136d40fcbdf87cd93eff713f82fa28172a5466686,통과raw2,502,749bytes/SHA256d439df23a389ba9099025722d38e7eb36bbf455f9f3c4e35bedf7b766cd68496. 최종소유잔여0/공유lockfree(boot5ca2452a-b323-4a82-a75a-ffbad896b59f)확인. source/freeze/과거FAIL/원본은변경하지않았다.

## Level2/3·총10회 작업(3447c9e8/v24 이후)

사용자의명세후실행지시에따라LEVEL23_EVALUATION_SPEC/PLAN을먼저작성했다. 단일작업자·추가질문없이실행한다. Level2(3,1,0.54)테이블/박스·5도ramp,Level3(3,1,0.04)식탁아래/1.1m문. 초기시야밖이므로소유된지도기반관측이동뒤fresh3D최종접근을연결한다. 총10slot은L2/L3교대각5회,실패/미완료/미실행포함분모10. 기존world높이20mm기준을이번결과에맞춰수정하지않는다. geometry치수는작업자선택이며명세에공개했다.

Ruling: 기존Task4와새계획이공유하는Scenario/goal/평가필드는새계획에정의하고이기록에L23 Task번호로진행상태를남긴다. Windows linked worktree의Git은Windows에서만다루며WSL Git경로를고쳐skill도구를억지로실행하지않는다. 재개시이ledger와commit을우선한다.
L23 Task1: in_progress. Task2/3/4: pending. 공식Nav21.3.13 static_layer.cpp와MuJoCo3.13.0 mjmodel.h를GitHub connector로읽었으며walkable지면/정적2D장애물/3D상판을분리하는기존API패턴을재사용한다. 이는물리성공증거가아니다.
L23 Task1~3 부품: world4 RED→5 PASS/3.77초,prearmed9 RED→관련20 PASS/3.23초,batch/world witness9 RED→전체382 PASS/58.80초. 이후관측지점/접근정적카메라2 PASS/6.95초를추가했다. full384를새로실행한것은아니다. full382production239파일/추가camera2시험전체370파일이v25freeze와일치PASS. build13.4초/설치67모듈·94자산actualchild감사PASS. source370/assets94 SHA256c31ad64b7ebeeaf2df2c30b56f6278335deb231bceb74860bf9dc49d31de54fa. Task1/2/3코드와부품은구현,실제연결은아직미확인. Task4사전실제L2부터확인한다. 본시험10slot은아직생성하지않았다.
L23 v25사전L2 UUID8b798b22-ed31-4222-a0ef-9cc075bcd2f1: 44.8sim/97.152wall초FAIL,실제ramp통과/접촉최대220.039N·survey도달/정착후최종관측대기에서실패했다. 첫1.4sim초cylinder not observed가TARGET_NOT_OBSERVED로latch돼vision accepted0/마지막처리1.4sim에고정됐다. 이는렌더가시성부품의실패가아니라새survey경로에기존영구부재fault정책을그대로연결한통합누락이다. worker/12child회수·lockfree. 본10회외개발실패로보존한다.

Ruling: survey를가진새scenario만최초accepted이전cylinder부재를계속기록하며관측한다 — 초기시야밖인명세와영구fault가충돌했다 — 좌표를생성하거나수명/TF/shape조건을완화하지않고첫실제검출뒤부재/legacy/redfixture부재는기존fault로유지한다. 공식vision_msgs/ros2 Detection3DArray의검출목록과센서고장구분을비교했지만해당message/API/의존성을추가한것은아니다. 2 RED확인후camera/원본수명회귀로검증한다. v25freeze/FAIL은수정하지않고v26새동결로분리한다.
v26初期부재2 RED→camera/원본수명포함28 PASS/27.71초(358 deselected). 같은시험snapshot과실행동결371개전수hash일치PASS. source371/assets94 SHA256b5f6db568696d808f11b80af88e7c5eccbab3036a9d3978475eb024d433cdc0b,설치67모듈actualchild/94자산감사PASS. v25실제실패source/archive를보존했다. 다음은가장불확실한L3문/식탁아래/관측이동연결을본10회이전에한번확인한다.
