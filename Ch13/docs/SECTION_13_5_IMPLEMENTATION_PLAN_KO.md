# 13.5 Crawl Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. 사용자 지정에 따라 네이티브 단일 작업자가 수행하며 서브에이전트·별도 리뷰 에이전트를 사용하지 않는다. 체크박스는 실제 실행 증거가 있을 때만 완료 처리한다.

**Goal:** 실제 통합 4족+팔 모델을 저속 crawl로 이동시켜 Nav2의 물체 접근·정지·취소를 양 엔진에서 검증하고 13.5 전용 브랜치로 게시한다.

**Architecture:** 짧은 센서·제어 루프, 긴 액션 통신, 실제 센서 worker를 분리한다. 다리는 crawl_controller, 팔은 carry_manager만 명령하며 motion_guard가 단일 이동 허용권을 관리한다. 물리 보행 게이트 G2가 통과하기 전에는 Nav2 접근 인수로 넘어가지 않는다.

**Tech Stack:** Ubuntu 24.04/ROS 2 Jazzy, Gazebo Harmonic, Python 오프라인 MuJoCo 3.3.7 / 고정 ROS C++ vendor MuJoCo 3.12.0, Python 3.12/NumPy 1.26.4, C++17/ament, 실제 Nav2·ros2_control. 기존 Ch13 카메라·제어기의 고정 외부 의존 버전을 유지한다. Task 4 빌드에서 실제 vendor 헤더와 underlay 링크를 확인해 버전 표기를 정정했다. 오프라인 결과는 실제 ROS 엔진 인수의 대체물이 아니다.

**Spec:** [사용자 승인 상세 설계](SECTION_13_5_CRAWL_NAVIGATION_DESIGN_KO.md), 설계 커밋 `231309a77da49ed54b312d5c79b4ff0278c00048`.

상태: **사용자 승인 — 구현 진행 중**. 아래 함수·파일·명령은 구현할 계약이며 각 Task의 실제 증거로 완료를 판정한다. 계획 승인만으로 시험이 통과했다는 뜻이 아니다.

## Global Constraints

- `sources/`, Ch01~Ch12, 외부 checkout/underlay는 수정하지 않는다. 필요한 복사는 출처·커밋·라이선스를 기록해 Ch13 내부로 한정한다.
- 사용자 지정 기존 checkout과 `feat/ch13-section-13-5`를 사용한다. 미추적 13.4 교육 문서는 보존하고 무관한 커밋에 포함하지 않는다.
- 실제 발 접촉으로 이동한다. root pose/velocity 강제 설정·명령 적분 odometry·외력/바퀴 대체 이동은 인수에 사용하지 않는다.
- 평탄한 바닥·고정 지도·정지 물체·`native_ground_truth` localization profile만 지원한다. PPO/trot/등반/SLAM/MoveIt/물리 파지를 완성했다고 주장하지 않는다.
- 제어 50Hz, `FL → RR → FR → RL`, `SHIFT → SWING → TOUCHDOWN → SETTLE`, 명목 stride phase-time8초, 수평 발 이동≤0.08m, swing 높이≤0.02m. Task8 실측 교정에 따라 부하/안정 대기 중 진행 시계는 멈추며 실제 물리 주기는8초보다 길 수 있다. 이를 고정8초 달성으로 주장하지 않고 G2/G4 진행률·deadline을 실측한다. 상세 근거와 비용은 설계서의 Task8 교정 및 실행 원장에 남긴다.
- 초기 속도 상한 전진 0.01m/s·횡이동 0·yaw 0.03rad/s, 가속도 전진 0.02m/s²·yaw 0.06rad/s². 후진은 같은 절대 선속도 상한을 적용하고 별도 실측한다.
- 지지 여유≥0.01m, 접촉 정상력≥2N, roll/pitch 절대값≤0.15rad, 몸체 높이 0.30~0.70m, stance slip≤0.02m.
- 관절·IMU·접촉·몸체의 ROS/수신 wall age 각각≤0.20초, raw 속도 입력 wall≤0.20초, scan≤0.30초. ROS와 monotonic을 서로 빼지 않는다.
- 13.4의 320×240·카메라 15Hz·추론 10Hz/선택 15Hz·촬영/수신 300ms·과거 TF 100ms·팔 명령 최대 5Hz를 유지한다.
- 일반 정지의 현재 swing 착지≤1초. 실측 선속도≤0.003m/s·yaw 속도≤0.01rad/s가 1초 유지돼야 STOPPED다.
- carry 목표 오차≤0.03rad·실측 속도≤0.02rad/s를 1초 유지한다. 미검증 후보 `[0,1.2,-2.0,0,0.8,0]`를 검증 없이 배포하지 않는다.
- 작업 위치 후보 거리 0.45/0.50/0.55/0.60/0.65m, nominal 0.55m, yaw 0/±15도. 목표 오차≤0.10m/≤0.10rad, 접근 deadline 240초·취소 결과 확인 5초.
- footprint는 허용 swept collision 투영+0.05m 여유를 포함하며 inflation_radius≥외접 반경+0.05m다. 낮은 장애물을 등반 가능하다고 무시하지 않는다.
- 실제 엔진은 순차 실행하며 소유 자식 회수·정상 종료·잔여 없음 확인 전 다음 엔진을 시작하지 않는다. 관리자·드라이버·ptrace 정책 변경은 없다.
- 실패를 보존한다. 자동 재활성화·무조건 재시도·인수 기준 완화로 통과시키지 않는다. 관련 시험 후 동결본으로 최종 전체 인수한다.

## Review Focus

1. 시계 pause와 smoothed 명령 반복: raw 명령·센서의 wall 만료를 가리면 안 된다. Task 5/6에서 실제 DDS·pause 회귀를 한다.
2. reset 뒤 늦은 센서·액션 응답: 이전 epoch/generation이 새 세션의 유효성이나 소유권을 갱신하면 안 된다. Task 1/4/7/11에서 검사한다.
3. 발 이름·힘 방향·단위·자기 ray: 틀린 접촉/scan으로 이동 허용을 얻으면 안 된다. Task 2/4/8에서 독립 native 관측과 대조한다.
4. carry 설정·모델 불일치: 오래된 검증 기록이나 영점 자세로 carry-ready를 얻으면 안 된다. Task 3/7에서 오염·교체·고착을 검사한다.
5. 관측과 목적지의 수명 혼동: 클라이언트 주장이나 재발행으로 카메라 수신 age를 갱신하면 안 된다. Task 10/11에서 cache 대조·지연·중복·변환 실패를 검사한다.

## 실행 환경과 공통 명령

실행 승인 후 저장소 루트의 **WSL**에서 설정한다. 기존 underlay/venv는 버전·경로를 확인한 뒤 재사용하며 이전 장 overlay는 source하지 않는다. 새 의존성 설치가 필요하면 먼저 진단·영향을 기록한다.

```bash
source /opt/ros/jazzy/setup.bash
source /home/jinho/ch13_mujoco_ws/install/setup.bash
source /home/jinho/ch13_vision_13_4_venv/bin/activate
export CH13_ROOT="$PWD"
export CH13_NAV_SRC="$PWD/Ch13/ros2_ws/src/integrated_robot_navigation"
export CH13_NAV_RUN=$(python -c 'import uuid; print(uuid.uuid4())')
export CH13_NAV_BUILD="$PWD/Ch13/ros2_ws/build13_5_$CH13_NAV_RUN"
export CH13_NAV_INSTALL="$PWD/Ch13/ros2_ws/install13_5_$CH13_NAV_RUN"
export CH13_NAV_LOG="$PWD/Ch13/ros2_ws/log13_5_$CH13_NAV_RUN"
export CH13_NAV_EVIDENCE="$PWD/Ch13/evidence/section_13_5/$CH13_NAV_RUN"
export ROS_DOMAIN_ID=159
export MUJOCO_GL=egl
```

아래 약칭은 반복되는 검증 명령을 뜻한다. 각 Task의 개별 시험을 먼저 실행한다.

- **BUILD:** `python -m colcon --log-base "$CH13_NAV_LOG" build --base-paths Ch13/ros2_ws/src --build-base "$CH13_NAV_BUILD" --install-base "$CH13_NAV_INSTALL" --executor sequential`. 성공 후 `source "$CH13_NAV_INSTALL/setup.bash"`.
- **UNIT:** `python -m pytest "$CH13_NAV_SRC/test" -q`.
- **ALL-SOURCE:** `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test "$CH13_NAV_SRC/test" -q`.
- **PACKAGE:** `python -m colcon --log-base "$CH13_NAV_LOG" test --base-paths Ch13/ros2_ws/src --build-base "$CH13_NAV_BUILD" --install-base "$CH13_NAV_INSTALL" --executor sequential`, 이어 `python -m colcon test-result --test-result-base "$CH13_NAV_BUILD"`.

명령마다 stdout/stderr·exit code·UUID를 보존한다. Task 8/13 실행기는 이를 자동 기록한다. 그 이전의 RED/GREEN 로그도 새 UUID 증거 디렉터리에 저장하며 기존 evidence를 재사용하지 않는다. ROS 시험은 별도 domain과 자기 소유 프로세스만 사용한다.

## 파일 배치와 공통 타입

경로 약칭은 `N = Ch13/ros2_ws/src/integrated_robot_navigation`, `S = Ch13/ros2_ws/src/integrated_robot_navigation_sensors`다. 셸 변수가 아니다. 아래 Python 모듈은 모두 `N/integrated_robot_navigation/`에 둔다.

| 위치 | 책임 |
|---|---|
| `samples.py`, `model.py` | 시각·이름·좌표 계약, URDF 기반 모델 계약 |
| `leg_kinematics.py`, `support.py`, `carry_profile.py`, `gait.py` | ROS 비의존 계산·검사 |
| `projection.py`, `motion_guard.py`, `crawl_controller.py`, `carry_manager.py` | ROS 경계·단일 소유권·lifecycle |
| `approach.py`, `action_transport.py`, `approach_coordinator.py` | 후보 계산·실제 Nav2 액션·상위 결과 |
| `N/config`, `N/maps`, `N/behavior_trees`, `N/launch`, `N/test` | 설정·world와 일치하는 지도·기동·회귀 |
| `S/include`, `S/src`, `S/test` | 읽기 전용 native 센서·C++ 회귀 |
| `Ch13/scripts/*13_5.py` | 오프라인 준비·소유 실행·독립 판정·전체 감사 |

공통 타입은 Task 1이 정의하며 후속 Task는 같은 이름·단위를 사용한다.

- `Vec3 = tuple[float,float,float]`, `JointMap = dict[str,float]`. 길이 m, 각도 rad, 시각 정수 ns다.
- `Sample`: `stamp_ns:int, received_ns:int, epoch:int, sequence:int, frame_id:str, data:object`. 수신 경계의 local monotonic으로 received_ns를 부여한다. 중복 sample은 최초 수신 시각을 유지한다.
- `SensorBundle`: `joints, imu, contacts, body, scan, carry`의 여섯 Sample. joints는 position/velocity JointMap, body는 실측 pose/twist, contacts는 이름별 접촉점/정상력, carry는 검증 기록/readiness다.
- `ModelContract`: `model_sha256:str, joint_names:tuple[str,...], feet:tuple[str,...], chains:dict, masses:dict, limits:dict`. 다리 순서는 FR/FL/RR/RL, 각 hip/thigh/calf다.
- `ControlResult`: `state:str, phase:str, swing_foot:str|None, generation:int, joint_targets:JointMap|None, reason:str`.
- `CarryProfile`: robot/config SHA256, 팔 6관절 목표, envelope, 엔진별 검증 artifact SHA256와 `offline`/`native_validated` 상태를 가진다.
- `ApproachCandidate`: `x:float, y:float, yaw:float, standoff:float, clearance:float, arm_solution:JointMap`.

## Task 1: 패키지·샘플 계약·실제 ROS 인터페이스

**Files:** Create `N/{setup.py,setup.cfg,package.xml,resource/integrated_robot_navigation}`, `N/integrated_robot_navigation/{__init__.py,samples.py,model.py}`, `N/test/{conftest.py,test_samples.py,test_interfaces.py}`. Modify `Ch13/tests/conftest.py`의 새 패키지 검색 경로. 기존 `integrated_robot_interfaces`에 `msg/{FootContacts,MotionState}.msg`, `action/ApproachObject.action`을 추가하고 `CMakeLists.txt,package.xml`에 등록한다. 기존 IDL 필드는 바꾸지 않는다.

**Interfaces:** `validate_bundle(bundle:SensorBundle,ros_ns:int,wall_ns:int,epoch:int)->tuple[bool,str]`, `compile_model(urdf:str)->ModelContract`. FootContacts는 header/epoch/sequence와 4개 발 이름·점·정상력·접촉 여부를 담는다. 점은 odom/m, 정상력은 N이다. MotionState는 header/generation/model hash/state/phase/swing foot/ready/stopped/fault reason을 담으며 carry/crawl 토픽을 구분한다. ApproachObject goal은 object_name/track_id/target_pose(PoseStamped)/source_header, result는 success/error_code/message/reached_pose, feedback은 current_state/distance_remaining이다.

- [x] **1 RED:** 먼저 G0 기존 소스·설치 기준을 확인한다. `test_duplicate_does_not_refresh_receipt`, `test_epoch_and_names`, 실제 IDL round-trip 시험을 쓴다. stamp=1초·최초 receipt=10초인 중복 sample을 11초에 받아도 receipt=10초이며 wall age 0.20초 초과로 거절됨을 assert한다. NaN/미래 시각/이름 중복도 거절한다.
- [x] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_samples.py" "$CH13_NAV_SRC/test/test_interfaces.py" -v`. 새 모듈/IDL 부재에 따른 RED를 기록한다. 무관한 환경 오류를 의도한 실패로 세지 않는다.
- [x] **3 GREEN:** 위 타입·검증을 구현하고 새 IDL을 생성한다. ROS ns와 monotonic ns를 명확히 분리한다.
- [x] **4 검증:** BUILD 후 같은 시험과 기존 인터페이스 시험이 모두 PASS인지 확인한다.
- [x] **5 커밋:** 이 Task 파일만 stage하고 `feat(ch13): define navigation sample and action contracts`로 커밋한다.

## Task 2: 실제 다리 IK·지지 여유·CoM

**Files:** Create `N/integrated_robot_navigation/{leg_kinematics.py,support.py}`, `N/test/{test_leg_kinematics.py,test_support.py,test_center_of_mass.py}`.

**Interfaces:** `fk_leg(model:ModelContract,foot:str,q:Vec3)->Vec3`, `ik_leg(model:ModelContract,foot:str,p:Vec3,previous:Vec3)->Vec3`, `support_margin(point:Vec3,contacts:list[Vec3])->float`, `center_of_mass(model:ModelContract,joints:JointMap,body_pose:object)->Vec3`. 도달 불가/한계 초과는 명시적 예외이며 clipping으로 성공시키지 않는다.

- [ ] **1 RED:** FR q=(0,-0.5,1)의 몸통 기준 발점은 `(0.25,-0.15,-0.438791280945)`m, FL의 y는 +0.15m임을 assert한다. ±0.2×±0.1m 사각형 중심 여유는 0.1m, 세 발 지지의 대각선 위 점은 0으로 lift 불가다. 질량 1@x0과 3@x0.4의 CoM x는 0.3m다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_leg_kinematics.py" "$CH13_NAV_SRC/test/test_support.py" "$CH13_NAV_SRC/test/test_center_of_mass.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 실제 URDF joint origin/axis/limit로 연속 IK 분기를 선택한다. CoM은 모든 실제 링크 질량·관절 자세로 계산한다.
- [ ] **4 검증:** 고정 seed의 비영점 자세에서 FK/IK 왕복 및 별도 native 오프라인 FK와 1e-5m 이내인지 확인한다. 실행 중 root를 강제 이동시키는 검증은 하지 않는다.
- [ ] **5 커밋:** UNIT 통과 후 `feat(ch13): add model based leg kinematics and support checks`로 커밋한다.

## Task 3: 검증 가능한 carry profile·보수적 footprint

**Files:** Create `N/integrated_robot_navigation/carry_profile.py`, `N/config/crawl_limits.yaml`, `N/test/{test_carry_profile.py,test_footprint.py}`, `Ch13/scripts/prepare_navigation_model_13_5.py`.

**Interfaces:** `prepare_profile(model:ModelContract,arm_q:tuple[float,...])->CarryProfile`, `validate_profile(profile:CarryProfile,model:ModelContract,engine:str)->tuple[bool,str]`, `swept_footprint(model:ModelContract,profile:CarryProfile,limits:dict)->list[Vec3]`. 준비 CLI는 `--output-dir NEW_PATH`를 받는다.

- [ ] **1 RED:** hash 불일치·간섭 자세·엔진 증거 없는 profile은 이동 허용 불가임을 assert한다. footprint가 길이 0.60m 몸통, 허용 다리·팔·기울기 envelope와 0.05m 여유를 모두 포함하는지 검사한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_carry_profile.py" "$CH13_NAV_SRC/test/test_footprint.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 단순한 몇 자세 샘플만으로 안전을 선언하지 않고 구간별 보수적 형상 경계를 사용한다. 원래 collision을 축소하지 않는다. 후보가 부적합하면 동결 전 대체 자세·선택 근거를 기록한다.
- [ ] **4 검증:** 준비 스크립트를 새 경로로 실행한다. 오프라인 profile은 Task 8 실제 G1 증거 전까지 CRAWL을 허용하지 않는다. robot hash는 로봇·actuator·default·물리 설정에 결합하고 전체 world/map hash는 별도 보존해 장애물 장면 변경과 로봇 변경을 구분한다.
- [ ] **5 커밋:** UNIT 통과 후 `feat(ch13): validate carry geometry and swept footprint`로 커밋한다.

## Task 4: navigation 장면·실제 센서·worker 소유권

**Files:** Create `S/{CMakeLists.txt,package.xml,LICENSE,REUSE_MANIFEST.md,navigation_plugins.xml}`, `S/include/integrated_robot_navigation_sensors/{snapshot.hpp,normalization.hpp}`, `S/src/{snapshot.cpp,normalization.cpp,native_navigation_plugin.cpp,navigation_sensor_probe.cpp,gazebo_com_observer.cpp}`, `S/test/{test_snapshot.cpp,test_normalization.cpp,test_plugin_lifetime.cpp}`. Create `N/config/{mujoco_navigation_plugins.yaml,navigation_bridge.yaml}`, `N/integrated_robot_navigation/{scene.py,gazebo_contacts.py}`, `N/test/{test_scene.py,test_gazebo_contacts.py}`. 기존 description의 `urdf/navigation_sensors.xacro`를 추가하고 `urdf/robot_system.urdf.xacro`, `launch/{mujoco,gazebo}.launch.py`의 선택 인수만 수정한다.

**Interfaces:** plugin ID `integrated_robot_navigation_sensors/NativeNavigationSensorsPlugin`. `normalization.hpp`에 C++ `NavigationSample`을 정의하고 `NavigationSample read_native(const mjModel*,const mjData*,uint64_t epoch)`로 읽는다. Python Sample과 구분한다. 출력은 `/navigation/foot_contacts`, `/navigation/imu`, `/scan`. `materialize_scene(engine:str,scenario:str,output:Path)->dict`는 world/map/robot hash를 반환한다.

- [ ] **1 RED:** native qpos/qvel/ctrl/xfrc가 plugin 호출 전후 불변, reset 후 이전 epoch 발행 0건, worker join 전 자원 파괴 불가를 assert한다. 360 ray에서 자기 로봇 제외·world 장애물 검출, 접촉 이름/정상력 부호·좌표 변환을 검사한다.
- [ ] **2 실행:** BUILD로 시험을 등록한 뒤 `python -m colcon test --build-base "$CH13_NAV_BUILD" --install-base "$CH13_NAV_INSTALL" --packages-select integrated_robot_navigation_sensors --event-handlers console_direct+` 및 해당 pytest로 의도한 RED를 기록한다.
- [ ] **3 GREEN:** MuJoCo worker는 전용 mjData/snapshot/epoch를 소유하며 live 상태·카메라/EGL worker를 공유하지 않는다. Gazebo는 native Contacts/IMU/scan을 bridge하고 고정 joint 결합 후 실제 collision 이름을 매핑한다. CoM observer는 엔진 링크의 실제 세계 pose/관성으로 독립 측정한다.
- [ ] **4 검증:** CTest/pytest PASS와 navigation=false의 기존 Xacro/launch 의미 보존을 확인한다. 외부 base class는 고정 underlay에 link하며 원본은 수정하지 않는다. 장면은 평지·작업대/컵·scan 높이의 우회 장애물로 만들고 root 이동/외력 plugin은 넣지 않는다.
- [ ] **5 커밋:** plugin 로드·읽기 전용·수명 시험 후 `feat(ch13): add owned native navigation sensing and scenes`로 커밋한다. 실제 센서 정확도는 Task 8에서 검증한다.

## Task 5: 평면 TF·raw 명령 만료·단일 이동 게이트

**Files:** Create `N/integrated_robot_navigation/{projection.py,motion_guard.py}`, `N/test/{test_projection.py,test_motion_guard.py,test_motion_guard_ros.py}`.

**Interfaces:** `project_body(sample:Sample)->Sample`, `MotionGuard.evaluate(bundle:SensorBundle,raw:Sample,smoothed:Sample,ros_ns:int,wall_ns:int)->tuple[Vec3,str]`. raw/smoothed/최종 `/navigation/cmd_vel`은 모두 Twist다. `/navigation/set_mode`는 기존 SetMode 타입으로 STAND/CRAWL/HOLD/STOP/RESET을 받으며 RESET 때 내부 generation을 증가시킨다.

- [ ] **1 RED:** 비영점 roll/pitch에도 nav_base z/roll/pitch=0, twist는 nav_base 기준, 기존 6D TF는 불변임을 assert한다. raw 중단 뒤 smoothed만 50Hz 재송신해도 0.20초 후 최종 출력은 0/fault여야 한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_projection.py" "$CH13_NAV_SRC/test/test_motion_guard.py" "$CH13_NAV_SRC/test/test_motion_guard_ros.py" -v`로 실제 DDS·ROS clock pause 상태의 RED를 기록한다.
- [ ] **3 GREEN:** `/odom`은 구독만 하고 `/navigation/odom`, `odom→nav_base`만 발행한다. 짧은 수신 executor와 steady watchdog을 분리한다. Twist raw는 원래 producer의 실제 수신 중단을 감시하고 센서 중복은 최초 receipt를 보존한다.
- [ ] **4 검증:** 중복 producer·carry 이탈·scan 만료·이전 generation 입력을 실제 DDS로 검사한다. 조건 복구 뒤에도 명시적 RESET/재허용 전에는 이동하지 않는다.
- [ ] **5 커밋:** UNIT 통과 후 `feat(ch13): gate motion with measured state and raw command expiry`로 커밋한다.

## Task 6: crawl 상태기계·50Hz 단일 다리 publisher

**Files:** Create `N/integrated_robot_navigation/{gait.py,crawl_controller.py}`, `N/test/{test_gait.py,test_crawl_lifecycle.py,test_crawl_safety_ros.py}`.

**Interfaces:** `CrawlMachine(model:ModelContract,limits:dict)`, `reset(bundle:SensorBundle,ros_ns:int,wall_ns:int)->None`, `advance(bundle:SensorBundle,command:Vec3,ros_ns:int,wall_ns:int)->ControlResult`, `request_stop(urgent:bool)->None`. crawl_controller만 `/leg_position_controller/commands`를 발행한다.

- [ ] **1 RED:** 세 지지 발의 접촉 또는 여유 0.01m 미달이면 lift=0, swing 발 수≤1, FL/RR/FR/RL 순서, NaN/IK/limit 실패 시 새 위치 목표=0건임을 assert한다. 일반 stop 뒤 새 몸체 진행=0, 신선한 입력에서 착지≤1초, feedback 손실 때 STOPPED 미확정도 검사한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_gait.py" "$CH13_NAV_SRC/test/test_crawl_lifecycle.py" "$CH13_NAV_SRC/test/test_crawl_safety_ros.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** SHIFT의 CoM 이동·stance 세계 위치 유지·연속 swing·실제 접촉 확인을 구현한다. bootstrap STAND는 carry 전에 가능하지만 CRAWL은 gate 허가가 필수다. 관절 이름/순서는 ModelContract를 따른다.
- [ ] **4 검증:** STOPPED는 실제 착지·속도 한계 1초로 판정한다. 시계 pause/역행·slip 0.02m 초과·inactive·이전 generation에서 새 보행을 금지한다. UNIT와 실제 lifecycle 시험을 통과시킨다.
- [ ] **5 커밋:** `feat(ch13): implement measured contact gated low speed crawl`로 커밋한다. 단위 시험만으로 실제 보행 성공을 선언하지 않는다.

## Task 7: 실제 FJT carry·시동 순서·배타적 launch

**Files:** Create `N/integrated_robot_navigation/carry_manager.py`, `N/launch/{navigation_sensors,crawl_system}.launch.py`, `N/test/{test_carry_manager_ros.py,test_carry_startup.py,test_navigation_ownership.py}`. Modify `N/setup.py,package.xml`.

**Interfaces:** carry_manager는 기존 ArmActionOwner/ArmActionTransport를 재사용하고 `/navigation/carry_state`에 MotionState를 발행한다. `carry_profile` 파라미터를 받는다. `validation_mode`는 STAND+carry 검증만 허용하고 CRAWL을 허용하지 않는다.

- [ ] **1 RED:** 실제 ROS FJT server에서 cancel ACK만 있음·지연 acceptance·terminal 미수신이면 ready=false, 목표 오차 0.03rad/속도 0.02rad/s가 1초 미만이어도 false임을 assert한다. hash 불일치·팔 고착·이전 generation·중복 팔 producer도 검사한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_carry_manager_ros.py" "$CH13_NAV_SRC/test/test_carry_startup.py" "$CH13_NAV_SRC/test/test_navigation_ownership.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 실제 STAND→carry FJT→terminal→실측 유지 1초→준비 순서와 종료 시 결과 drain/receiver join을 구현한다. 그리퍼도 carry owner만 무부하 자세를 유지하며 파지 완료로 부르지 않는다.
- [ ] **4 검증:** 실제 launch graph에서 기존 locomotion/manipulation/tracking requester가 중복 기동되지 않는지 확인한다. 기존 비navigation launch는 기존 노드 그대로인지 검사한다. BUILD/UNIT를 통과시킨다.
- [ ] **5 커밋:** `feat(ch13): add verified carry startup and exclusive crawl launch`로 커밋한다.

## Task 8: G1/G2 실제 엔진 실행·독립 인수 판정

**Files:** Create `Ch13/scripts/{run_navigation_13_5.py,probe_navigation_13_5.py,verify_navigation_13_5.py}`, `N/test/{test_evidence_13_5.py,test_native_verdicts.py}`.

**Interfaces:** runner CLI `--engine mujoco|gazebo --scenario sensors-carry|crawl-cycle|crawl-reverse --profile PATH --output-dir NEW_PATH`. `assess_crawl(observations:dict,limits:dict)->dict`는 실측으로 필수 check를 판정하며 누락은 FAIL이다. 실행기 exit code와 결과 FAIL을 구분해 모두 보존한다.

- [ ] **1 RED:** 명령 기록만 있음·합성 odometry·접촉/CoM 누락·강제 cleanup·잔여 PID가 PASS가 되지 않도록 시험한다. 전진 0.40m/좌우 yaw 각 0.30rad, 위치 오차 0.05m·yaw 오차 0.10rad·yaw 중 표류 0.05m 경계를 assert한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_evidence_13_5.py" "$CH13_NAV_SRC/test/test_native_verdicts.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 소유 PGID/PID/start tick을 추적하고 기존 13.4 정상 종료·부모 회수를 재사용한다. 실제 센서·관절·접촉·native CoM/root pose·ctrl·FJT 결과·라이브러리 경로·소스/설치 bytes를 수집한다.
- [ ] **4 G1:** MuJoCo→정상 정리→Gazebo로 정적 체중 분배·단일 발 lift·IMU/frame/scan·carry를 실측한다. 실제 PASS artifact/hash만으로 엔진별 profile을 native_validated로 승격한다. 미검증 profile의 CRAWL 거절도 실제 확인한다.
- [ ] **5 G2/커밋:** 각 엔진에서 `정지10초→전진0.40m→좌0.30rad→우0.30rad→STOPPED`를 새 실행으로 3회 연속 확인하고 후진 0.10m도 별도 실측한다. Global Constraints의 자세/높이/지지/미끄러짐을 모두 적용한다. 첫 FAIL에서 중단·증거 보존·근인/TDD 수정한다. PASS 후 `test(ch13): verify native crawl and carry gates`로 커밋한다.

**게이트:** G1/G2 미달이면 아래 Nav2 성공 기능을 계속 덧대어 완료로 취급하지 않는다. 여러 최소 수정이 실패하면 지지/제어 설계를 재검토하되 합성 이동으로 대체하지 않는다.

## Task 9: 실제 Nav2 스택·지도·스무더·충돌 정지

**추가 운영 지시(2026-10-25):** 현재G1/G2 게이트를마무리한뒤아래남은Task는
성공사례/공식구현을먼저조사하고구현한다. 조사에서는실제사용한ROS배포판·시뮬레이터·
명령/TF/관절소유권·센서·정지/종료·라이선스·고정커밋을기록한다. 영상/README의
성공주장과실행가능소스/시험증거를구분하고, 우리시스템과다른동역학/센서/가정은
그대로이식하지않는다. 한Task당채택할구조와제외할구조·이유를먼저정하고,
차이를판별하는최소시험→구현→실측으로진행한다. 근거없이설정의모든조합을
순회하지않으며, 기존인수기준은유지한다.

**Files:** Create `N/config/nav2_params.yaml`, `N/maps/navigation.yaml`, `N/behavior_trees/navigate_crawl.xml`, `N/launch/navigation.launch.py`, `N/test/{test_nav2_configuration.py,test_nav2_bringup_ros.py,test_collision_stop_ros.py}`. 지도 이미지는 scene 생성기의 기계 생성 산출물로 world와 함께 hash 관리한다.

**Interfaces:** 실제 Nav2 planner/controller/BT/lifecycle/smoother, 단일 map→odom profile, nav_base, raw→smoothed→guard의 Twist 경로를 구성한다. launch 인수는 engine/profile/world/map/localization=`native_ground_truth`다.

- [ ] **1 RED:** 실제 launch/config 평가로 단일 clock/TF/명령 producer·vy=0·속도/가속도 한계·미검증 Spin/BackUp 복구 없음이 성립하는지 assert한다. YAML 문자열 검색만으로 실행 구성을 검증하지 않는다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_nav2_configuration.py" "$CH13_NAV_SRC/test/test_nav2_bringup_ros.py" "$CH13_NAV_SRC/test/test_collision_stop_ros.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 지도·scan·frame·footprint를 일치시키고 Jazzy의 Twist 설정을 명시한다. 스무더는 50Hz/CLOSED_LOOP, `/navigation/odom`, timeout 0.20초를 사용한다. raw 수신 감시·steady watchdog을 별도로 유지한다.
- [ ] **4 검증:** 실제 Nav2 active·경로 생성·속도 출력과 collision monitor/guard의 스무더 이후 즉시 0 출력을 확인한다. 침입 장애물은 고정 seed의 사전 정의 fixture를 사용한다. 엔진은 소유 실행기로 순차 관리한다.
- [ ] **5 커밋:** BUILD/UNIT와 관련 실제 시험 후 `feat(ch13): bring up real Nav2 for guarded crawl navigation`로 커밋한다.

## Task 10: 작업 위치 후보·진짜 비전 입력·도달 가능성

**Files:** Create `N/integrated_robot_navigation/approach.py`, `N/test/{test_approach_candidates.py,test_target_admission.py}`.

**Interfaces:** `admit_target(goal:object,cache:dict,ros_ns:int,wall_ns:int)->Sample`, `candidates(target:Vec3,robot:Vec3,arm_mount:Vec3)->list[ApproachCandidate]`, `select_candidate(candidates:list[ApproachCandidate],costmap:object,footprint:list[Vec3],arm_ik:object,path_cost:object)->ApproachCandidate`. 해가 없으면 명시적 실패를 반환한다.

- [ ] **1 RED:** obj=(1,0), robot=(0,0), mount=(0,0), d=0.55 후보는 x=0.45/y=0/yaw=0임을 assert한다. robot=obj·NaN·전 후보 간섭/IK 불가·지도 unknown/범위 밖·미래/만료/동일 stamp 재송신을 거절한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_approach_candidates.py" "$CH13_NAV_SRC/test/test_target_admission.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 서버가 실제 받은 `/vision/tracked_target`의 local cache와 Goal의 track_id/source_header/pose를 대조한다. 원격 monotonic 값이나 Goal만으로 촬영/수신 300ms를 증명하지 않는다. 과거 TF 100ms 실패는 실패로 처리한다.
- [ ] **4 검증:** navigation anchor로 고정해도 원래 source header를 별도 보존한다. Nav2 요청 stamp와 원 관측 stamp를 혼동하지 않는다. 보이는 컵 표면점과 중심/파지 pose를 동일시하지 않는다. 거리·자세·clearance·path 순위와 동점 규칙을 고정하고 실제 모델 arm IK/footprint 회귀를 통과시킨다.
- [ ] **5 커밋:** UNIT 후 `feat(ch13): select feasible approach poses from admitted vision targets`로 커밋한다.

## Task 11: ApproachObject·실제 Nav2 결과·취소·안정 정지

**Files:** Create `N/integrated_robot_navigation/{action_transport.py,approach_coordinator.py}`, `N/test/{test_navigation_action_owner_ros.py,test_approach_coordinator_ros.py}`.

**Interfaces:** `NavigationActionOwner`는 기존 팔 owner의 예약→acceptance→result→해제 계약을 Nav2 타입에 적용한다. `ApproachCoordinator`는 ApproachObject server, ComputePathToPose/NavigateToPose clients, motion gate SetMode client를 가진다. 팔을 직접 명령하지 않는다.

- [ ] **1 RED:** 실제 ROS 액션 server/client에서 status/cancel ACK만으로 해제하지 않음, 서버 result가 있어도 클라이언트 미수신이면 미완료, 상위 이중 Goal 거절, 이전 generation 결과로 재시동 불가를 assert한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_navigation_action_owner_ros.py" "$CH13_NAV_SRC/test/test_approach_coordinator_ros.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 결과 수신 전용 executor와 유계 계획/통신 처리를 분리한다. 접근 240초·취소 5초 wall deadline 및 feedback을 구현한다. 취소/성공 경합에서는 실제 하위 결과와 상위 취소/settle 판정을 따로 기록한다.
- [ ] **4 검증:** 상위 성공은 하위 실제 SUCCEEDED+실측 위치≤0.10m/yaw≤0.10rad+STOPPED 1초+carry 유지가 모두 필요하다. 취소 미확정은 fault-held다. 소유하지 않은 공유 Nav2 lifecycle을 종료하지 않는다. 실제 Nav2의 완료·취소 소시험을 수행한다.
- [ ] **5 커밋:** UNIT와 소시험 후 `feat(ch13): coordinate approach with confirmed Nav2 results and settling`로 커밋한다.

## Task 12: G3/G4 실제 접근·고장 주입 matrix

**Files:** Extend `Ch13/scripts/{run_navigation_13_5.py,probe_navigation_13_5.py,verify_navigation_13_5.py}`. Create `N/test/{test_fault_matrix.py,test_approach_verdicts.py}`.

**Interfaces:** scenario는 `approach-front|approach-diagonal|obstacle-detour|blocked|cancel|intrusion|fault`를 추가한다. fault는 `raw|scan|joints|imu|contacts|body|carry|clock|duplicate_owner|ik`. 매 실행 새 UUID/output을 요구한다.

- [ ] **1 RED:** native 이동 0.60m 미만·Nav2 status만 있음·STOPPED 미확정·오래된 비전 재포장·실제 충돌·실제 미주입 고장을 PASS로 세지 않도록 assert한다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_fault_matrix.py" "$CH13_NAV_SRC/test/test_approach_verdicts.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 자기 소유 실행의 입력 차단·시험 producer·engine pause로 G3를 주입한다. fault 시각부터의 새 명령·실제 몸체 속도·소유권 결과를 수집하며 모르는 PID는 중단하지 않는다.
- [ ] **4 G4:** 각 엔진의 실제 RGB-D 목표로 정면/대각·장애물 우회·도달 불가·취소·침입 정지를 검증한다. 고정 YOLO 컵 인식과 색상 fixture 결과를 구분한다. ground truth 좌표를 비전 Goal로 주입하지 않는다.
- [ ] **5 커밋:** 필수 case 전체와 실제 증거를 확인해 `test(ch13): verify guarded native navigation and failure handling`로 커밋한다.

## Task 13: 8패키지 감사·동결 전체 matrix·13.3/13.4 회귀

**Files:** Create `Ch13/scripts/verify_all_13_5.py`, `N/test/{test_full_manifest.py,test_required_checks.py,test_installed_navigation.py}`. 기존 13.4 실행기/required_checks는 필요 없이 바꾸지 않는다.

**Interfaces:** `snapshot_13_5(repo:Path)->dict`, `audit_navigation_install(prefix:Path,repo:Path)->dict`. CLI `--install-prefix PATH --output-dir NEW_PATH --weights PATH --group source|package|g1|g2|g3|g4|legacy|all`. Ch13/scripts/tests와 전체 8패키지 bytes를 고정한다.

- [ ] **1 RED:** 오래된 overlay·누락 신규 패키지·소스/설치 불일치·미실행 case·3회 중 1회 FAIL·강제 종료를 PASS 집계하지 않도록 assert한다. 기존 13.4 required_checks 집합 축소도 FAIL이다.
- [ ] **2 실행:** `python -m pytest "$CH13_NAV_SRC/test/test_full_manifest.py" "$CH13_NAV_SRC/test/test_required_checks.py" "$CH13_NAV_SRC/test/test_installed_navigation.py" -v`로 RED를 기록한다.
- [ ] **3 GREEN:** 기존 6패키지 감사에 신규 Python/config/assets 및 sensor source manifest/.so 실제 mapping을 더해 8패키지를 감사한다. 13.4 자식의 6패키지 submanifest를 부모 8패키지 동결본과 대조하고 나머지도 부모가 실행 전후 감사한다.
- [ ] **4 검증:** ALL-SOURCE/PACKAGE/설치 감사→코드 동결→`python Ch13/scripts/verify_all_13_5.py --install-prefix "$CH13_NAV_INSTALL" --output-dir "$CH13_NAV_EVIDENCE/final" --weights "$CH13_YOLO_WEIGHTS" --group all`. weights 경로/hash는 기존 검증 자산에서 확인해 설정한다. G1~G4, 양 엔진 도착·취소·정상 종료 각 3회 연속, 기존 13.4 원래 20회+Gazebo 추가 추적 2회 및 양 엔진 13.3 회귀를 실행한다. MuJoCo 10/15Hz 추적 각 3회를 보존한다.
- [ ] **5 커밋:** 첫 FAIL에서 batch를 멈추고 수정 후 새 동결본을 만든다. 전체 PASS 시 artifact size/hash·명령·결과 UUID·부모 회수·잔여 없음을 독립 집계해 `test(ch13): record frozen section 13.5 native acceptance`로 커밋한다. 이후 runtime 수정은 영향받은 실제 시험 재실행이 필요하다.

## Task 14: 한글 실습·리뷰·증거·non-force 게시

**Files:** Create `Ch13/docs/{LAB_13_5_GUIDE_KO.md,SECTION_13_5_REPORT_KO.md,SECTION_13_5_REVIEW_KO.md}`. Update `Ch13/docs/REUSE_MANIFEST.md`. Create `Ch13/evidence/section_13_5/<UUID>/README.md`와 게시 확인 기록.

**Interfaces:** 가이드는 Ch13 단독 빌드·설치·실행·정지, 보고서는 원고와 구현 차이·실패 이력·실측·미검증, 리뷰는 단일 작업자 자체 검토의 한계를 명시한다.

- [ ] **1 대조:** 새 설치본으로 가이드 명령과 실제 결과를 대조한다. crawl을 PPO/토크 제어, native_ground_truth를 SLAM, 접근을 물리 파지로 부르지 않는다.
- [ ] **2 검토:** 사양 대응·타입/단위·소유권·시각·정지/종료·출처·미검증을 자체 리뷰한다. runtime을 고치면 실제 영향 시험을 재실행하며 문서만으로 수정을 완료 처리하지 않는다.
- [ ] **3 커밋:** 링크·명령·설치 manifest·`git diff --check`·이전 장 무변경·사용자 미추적 문서 보존을 확인해 관련 파일만 커밋한다.
- [ ] **4 게시:** 동명 원격 ref를 다시 확인한다. 독립 이력이면 merge/force하지 않고 접미사 브랜치를 사용한다. `git push -u origin HEAD:refs/heads/feat/ch13-section-13-5`로 non-force 게시하고 `git ls-remote --heads origin <실제 브랜치>`의 SHA를 로컬 HEAD와 비교한다. 접미사를 썼으면 두 명령 모두 실제 이름을 사용한다.
- [ ] **5 보고:** 해결한 원인·양 엔진 결과·남은 제약·문서·원격 브랜치/SHA를 간결하게 보고한다. main 병합·PR은 하지 않는다. 미달 게이트가 있으면 완료로 위장하지 않고 재현 가능한 차단 요인과 필요한 결정을 제시한다.

## 계획 자체 검토·실행 인계

이 계획은 하나의 강하게 연결된 제어 경로를 14개 검증 단위로 나눈다. 각 Task 안에서는 작은 RED/GREEN/커밋을 반복하며, 네이티브 단일 작업자가 순서대로 수행한다. 기존 성공 로그를 재실행 없이 새 결과로 취급하지 않는다.

- [x] 설계 각 요구를 Task 1~14에 배치하고 실제 crawl 검증을 Nav2보다 앞에 뒀다.
- [x] Review Focus 다섯 조건을 구체적 회귀에 배치했다.
- [x] 시각·기하·결과/소유권·profile의 타입과 단위를 대조했다.
- [x] G0~G5·실패 보존·최종 전체 회귀·원격 SHA 검증을 포함했다.
- [x] 사용자가 구현 계획을 검토하고 권장 방향으로 승인했다.
- [x] `superpowers:executing-plans`로 네이티브 단일 구현을 시작했다.

이 계획 작성 중 제품 코드·IDL·패키지·센서·엔진은 구현하거나 실행하지 않았다. 본문의 PASS 조건과 수치는 실행 완료 결과가 아니다.
