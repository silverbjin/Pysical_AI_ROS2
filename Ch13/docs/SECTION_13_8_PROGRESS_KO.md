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
