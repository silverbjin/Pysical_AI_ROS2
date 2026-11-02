# Ch13 13.2 재사용·출처 명세

## 13.5 추가 — 구현 진행 중

- 2026-11-02: gait의 `maintenance`는 Ch13 자체 same-cycle/기존 XYZ 커널을 재사용한다. 선택 발의 원래 envelope를 현재 한 점으로 좁히고 현재 측정 힘을 목표로 사용한다. 외부 코드·의존성·게인·실제 actuator는 변경하지 않는다. 실패264의 독립 Farkas 증명과 기존 실제 기록의 반사실 후보는 자체 evidence이며, 68,717B `native_ab85_maintenance_window.json`은 원본/진단 SHA를 기록한 회귀 fixture다. 반사실 관측은 실제 물리 성공으로 세지 않는다.

- 2026-11-02: `load_process.py`의 유계 `transact()`와 gait의 명시적 Gazebo G2 `same_cycle`은 자체 구현이다. 기존 수치 자식·socket·단일 RX·조건변수·exact kernel을 재사용하며 새 프로세스/권한/의존성은 없다. 외부 소스는 복사하지 않았다. 원래 worker lifecycle/40ms/200ms/10ms 커널 검사를 보존하고 전체 거래10ms를 추가한다. 실제 성공 job325와 새 관측의 부모 거부 fixture는 자체 evidence에서 결합했으며 과거 실패·기본/MuJoCo 비동기 동작을 보존한다.

- 2026-11-02: sensors의 `inverse_remainder.hpp`와 servo 제약 보수화는 기존 Ch13 3DoF 다리 FK에서 자체 유도했다. `sin/cos≤1`의 전역 Hessian 상계와 국소 역함수 contraction으로 IK 나머지를 제한한다. 외부 코드 복사·새 의존성은 없으며, SEIKO는 actuation-feasibility 설계 참고다. 원래 정확한 토크·기하·시간 검사와 vendor QPMAD 원본은 유지한다. 실패 fixture121은 자체 실제 evidence에서 ID를 대조해 추출했고 원본 실패를 보존했다.

- 2026-11-01: `runtime_cpu_probe.py`와 관련 시험은 Python 표준 라이브러리로 자체 작성했다. 기존1Hz 실행기 계측에서 원본 클록 bracket와 소유 프로세스 스레드의 Linux proc 카운터만 유계 읽기하며 ROS·권한·시계·priority·affinity·제어 입력을 변경하지 않는다. 분석용 NumPy 스레드 비교는 [OpenBLAS runtime 변수](https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/)와 [공식 조회 함수](https://www.openmathlib.org/OpenBLAS/docs/extensions/)를 참고했지만 이 환경에서는 실제 NumPy 프로세스가 양쪽1스레드여서 변경을 채택하지 않았다. 추가 패키지/외부 소스 복사는 없다. smooth 실측 실패 후 G1 선택은 기존 bounded로 복원하고 실험 코드·증거는 보존한다.

- 2026-11-01: G1 `bounded_preload_smooth`는 Ch13 자체 `calibration.py`의 기존 quintic 속도 적분·가속도/jerk 계획을 재사용한다. 명시적 Gazebo native G1 검증에만 선택하고, 기존 일반 bounded/MuJoCo loaded/G2 선택을 유지한다. 외부 소스/의존성/컨트롤러/명령 권한 추가0이며 원본 endpoint·20mm/s·0.2m/s²·10초/1초·접촉·lift·모터 기준을 보존한다. seed 거리/실측은 자체 G1 `1e7eda2b` 실패에서 추출했으며 실패를 보존한다. reference 곡선 검사는 실제 안정화 성공의 대체물이 아니다.

- 2026-11-01: 늦게 소비된 수치 응답의 수명 정리·유계 수신 시각 메타데이터와 `CrawlMachine`의 모델 검사 전 단일 완료 수집은 Ch13 자체 코드다. 기존 숫자 자식/소켓/부모 콜백을 재사용하며 외부 복사·새 의존성·스레드·명령 권한을 추가하지 않는다. 원래40ms 수집 기한/10ms 계산·32회·원본200ms를 유지하고 적용 시각의 원본 receipt age도 검사한다. STOP/reset/fault는 완료 슬롯을 폐기한다. 원본 C1 `9b6038a5`의 실패와 정상 종료 미달은 보존한다.

- 2026-11-01: `native_complete_xyz.py`와 sensors의 complete XYZ ABI1은 Ch13 자체 코드다. 기존 Ch13 mass/contact ABI1·QPMAD1.5.1 XYZ ABI1·reference ABI1을 같은 수학/28표본으로 연결하고 Python I/O 버퍼만 재사용한다. 외부 복사·새 의존성·이전 관측/해 캐시는 없다. 외부 QPMAD의 고정 출처/라이선스는 sensors `REUSE_MANIFEST.md`와 `third_party/qpmad/UPSTREAM.json`을 유지한다. 준비/실행/종료에 새 kernel backend·ABI·해제 증거를 요구하며, 기존10ms/32회/40ms와 모든 물리 제약을 그대로 검사한다. 실제C1 `9c62136f` 실패 입력은 자체 evidence에서47140바이트로 최소 추출했고 원본 실패를 보존했다.

- MuJoCo G1 relay100의 직접 직렬 모델 실행과 숫자 전용 wall/thread-CPU 경계는 기존 Ch13 G2 구현을 재사용한다. rclpy7.1.12 commit `bd637294dd02b1c128422395c059fa06df8387a3`의 `executors.py`(blob `7a04710532226c2ed29a08e25174ff11661bfa6a`)에서 직접 실행/worker 제출 경계를 확인했으며 외부 코드는 복사하지 않았다. G1의 wall50Hz·20ms 참조 규칙·wait-set ingress와 기존 native 모터 적용은 유지한다. 실제073ad2cb 실패 및 새 비교 설계는 `SECTION_13_5_INGRESS_CAPACITY_KO.md` 참조.

- 2026-10-28: 사용자 승인 보존 정책의 `evidence_retention_13_5.py`와 회귀, 자동 시동/종료 점검은 Python 표준 라이브러리로 자체 작성했다. 외부 코드 복사는 없다. 기존 성공 기준·원래 결과 파일은 유지하고, 비대표 원본을 제거한 사실을 별도 원장으로 명시한다. 과거의 전체 원본 영구 보존 문구는 `EVIDENCE_RETENTION_POLICY_KO.md`로 대체한다.

- MuJoCo G2 relay100 수신 전용 실행기는 설치된 rclpy7.1.12 `EventsExecutor` 공개 API를 사용한다. 태그/commit `bd637294dd02b1c128422395c059fa06df8387a3`, Apache-2.0. 기존 Ch13 `event_compatible_callback`의 MessageInfo 호환을 재사용하며 외부 코드는 복사하지 않는다. backend는 수신 시작 전에만 선택하고 모델/기본/G1/Gazebo 실행기는 유지한다. 근거·실제 DDS 비교와 회귀는 `SECTION_13_5_INGRESS_CAPACITY_KO.md`에 기록한다.

- 2026-10-28: `native_observer_13_5.py`·C++ 원본 수신기·CDR reader/수명 회귀는 Ch13 자체 작성이다. rosbag2 0.26.11(commit `cb8fa198b93bfed90e2417b52b8645fb9ef89c2b`)의 직렬 메시지 수명 원칙을 참고했으며 외부 코드는 복사하지 않았다. 구체 API·출처는 sensors 패키지 REUSE와 `SECTION_13_5_NATIVE_OBSERVER_PLAN_KO.md`에 있다. 기존 Ch13 normalizer/`SensorInbox`/프레임 계산을 명시적 원본 receipt/cutoff로 재사용한다. 독립 ACK 관측은 제어 클라이언트의 receipt/credit을 대신하지 않는다. 현재17개 새 회귀16.84초 PASS이며 실제 엔진 성공은 별도다.
- 2026-10-28: `AppliedReferenceCredit`의 기한 안에 촬영·첫 수신된 유효 ACK 검사 순서, 실패 ingress/credit snapshot과 회귀는 자체 작성이다. 촬영·첫 수신·현재 나이 각각200ms를 유지한다. RED→관련32PASS35.30초로 확인했으나 CF 실제 ACK 첫 수신이 미기록이라 단독 원인 확정/실제 해결로 주장하지 않는다.
- 2026-10-28: 사용자 요청으로 검증된 중복 증거3,692,695,699bytes와 재생성 캐시625,628,861bytes를 정리했다. 원본·ZIP의 SHA/CRC·Git 소유 범위를 대조했고 복원 목록과 `SECTION_13_5_STORAGE_CLEANUP_KO.md`를 남겼다. 외부 checkout·원본 실패·현재 native 설치·사용자13.4 교육 파일은 보존했다.

- G2 전용 검증 프로필은 사용자 승인(2026-10-25)에 따라 기존 Ch13 G1 장면·
  relay100/20ms/50µm 선택을 동일 해시로 재사용한다. 기본·일반 프로필은 유지한다.
  신규 `admission.py`, `execution_contract.py`, `g2_command_source.py`, `g2_sequence.py`는
  Ch13 자체 구현이며 외부 소스 복사가 없다. 실제 G1 증거 전체 해시 검사는 시동 때 수행하고
  이후 파일 identity 변경은 sticky 실패로 처리한다. G2 fixture 명령원은 Nav2/PPO가 아니다.
- 정상 crawl의 계획 착지 끝점 완료 수정은 Ch13 G1의 '접촉 후에도 원래 참조까지 유계 복귀'
  원리를 재사용한다. G1 수직 궤적은 그대로 두고 정상 SWING 조기 중단만 제거한다.
  99ee5235 실제 q/body/contact fixture는 자체 엔진 evidence에서 최소 추출했으며 원본 보고서
  SHA를 기록했다. 과거 실패·외부 underlay·기존 장을 변경하지 않는다.
- G2 guard의 허가 I/O 분리는 기존 Ch13 runtime `common.DrainingExecutor`를 재사용한다.
  별도 서비스 callback group은 rclpy 공개 API이며, 기본/G1 직렬 EventsExecutor는 유지한다.
  native G2 3299043b의 원래 clock 정체와 실제 DDS 지연 회귀에 근거한 자체 변경이다.
  외부 rclpy 구현·underlay를 복사하거나 수정하지 않는다.
- G2의 journal/cache 분리는 자체 `NavigationProbe`의 원본 JSONL을 재사용한다.
  live128개 cache와 종료·join 뒤 전체 복구를 분리하며, GC 정책을 바꾸지 않는 Python
  표준 `gc.callbacks` 계측을 추가했다. 외부 라이브러리/코드 복사는 없다.
  모든 원본 frame·controls·몸체 참조·TF의 기록/복구 건수 일치와 손상 거부를 검사한다.
- 정상 crawl의 합성 몸체 시간 법칙은 자체 `blend` quintic과 기존 제한값에서 유도했다.
  외부 궤적/보행 코드 복사나 게인 튜닝이 아니다. G1의 별도 제자리 궤적은 유지한다.
  일반 이동에서 offset뿐 아니라 travel·입력 ramp·회전 기여까지 가속도 예산에 포함한다.
- 실측 stance anchor와 명령 `_targets`의 분리는 기존 reset의 Ch13 의미를 정상 착지·STOP에
  일관되게 적용한 자체 수정이다.69f58225 실제 q/body/contact fixture와 원본 보고서 SHA를
  기록했다. 실측20mm 한계·명령 연속성·G1 기준을 유지하며 외부 코드 복사는 없다.
- G2 transport 계측은 기존 자체 `transport_receipt`와 실제 rclpy MessageInfo를 재사용한다.
  FootContacts의 원래 native sequence/epoch는 별도 trace에 보존하고, 정규화 Sample 순번이나
  촬영 시각은 바꾸지 않는다. 외부 publisher/SDK·실행기·QoS 변경 없는 자체 계측이다.

- 50µm 수치접촉비교는 기본관측과구분한 G1 전용 opt-in이다. Ch13 신규
  `dart_contact`와native읽기전용probe가설치DART6.13.2 공개API/CMake target에
  link하며외부BSD소스복사·수정은없다. 동일실제Gazebo PID의기존3개Ch13라이브러리에
  실제DART provider의path/inode/device/SHA검증을추가한다. 원래23검사와relay검사를
  보존하고별도설정검사를추가한다. 기존profile의`physics_sha256`는오프라인MJCF
  의미를유지하고,추가`native_physics_sha256`가생성URDF/SDF/world와두실험모드를묶는다.
  기준checkpoint3fd278c/사용자승인2026-10-25. 실제전체인수전일반보행허가는없다.

- G1 전용 native 명령 연속 적용은 기존 Ch13 `PositionPDSystem`의 opt-in 확장이다.
  Gazebo8.15 공개 `Component`/`Factory`/`VectorDoubleSerializer`를 사용하는
  Ch13 신규 `position_reference.hpp`는 진단용 입력/적용값·write시각을 보관하며
  외부 구현 파일 복사나 physics 위치/속도 쓰기가 아니다. 기본설정·일반CRAWL·
  팔/그리퍼·게인/감쇠/힘상한은 유지한다. `scene.py`가 생성 URDF·메타데이터를 묶고
  `crawl_system.launch.py`가 validation 외 사용을 거부한다. 기준 HEAD7f321ebb,
  사용자 승인2026-10-24. 외부 underlay/드라이버/권한 변경은 없다.

- G1의 `calibration.py`와 `CrawlMachine.confirm_contact_calibration`은 Ch13 신규
  코드다(재설계 기준 HEAD `7f321ebb4141089a09e06d5c646ac83d180fc906`). 사용자 승인에
  따라 초기 상승 참조를 기존 가속도 상한으로 감속한 뒤, 원래 rest까지 해석적
  삼각형/사다리꼴 속도곡선으로 복귀한다. 외부 궤적 라이브러리나 제어기 소스 복사는
  없다. 기존 `CrawlController._stand_ready`의 실제1wall초 판정이 성공한 뒤에만
  G1 소유권을 해제하며 원래10wall초 deadline을 유지한다. 일반 CRAWL·게인·
  액추에이터/TF 소유권은 바꾸지 않는다. 순수/이상추종/ROS 회귀는 실제 물리 인수가 아니다.

- navigation 전용 Gazebo direct-child 실행은 설치된 `ros_gz_sim/launch/gz_sim.launch.py`의
  `GazeboRosPaths.get_paths()`와 실행 파일 조회 함수를 import해 기존 plugin/resource
  환경을 그대로 재사용한다. 외부 launcher를 복사·수정하지 않는다. Ch13에서만
  인수를 분리한 `ExecuteProcess(shell=False)`로 Ruby/native 엔진을 직접 소유한다.
  기존13.4/일반 launch는 기존 IncludeLaunchDescription 경로를 유지한다. runtime
  감사에 source/설치 description launch 두 파일의 bytes와 외부 helper 경로/SHA를 기록한다.

- CoM의 측정 단위 공통경로 캐시·하중 이동의 협력식 탐색·Crawl guard 미래 시각 선택과
  최초 실패 snapshot은 Ch13 신규 코드다. 변환 계산은 기존 Ch13
  `integrated_robot_vision.kinematics.KinematicChain`의 고정 compiled tuple 계약
  (재사용 기준 `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`)을 읽으며 외부 소스 복사가 아니다.
  guard 후보 선택은 같은 Ch13 `SensorInbox`의 촬영 시각 eligibility 원칙을 적용했다.
  원래 ROS/monotonic 시각과 모델·명령 소유권을 유지하고 실제 엔진 증거와 단위 시험을 구분한다.

- Gazebo 실제 제어값 관측의 API 조사 기준은 설치 패키지 `ros-jazzy-gz-ros2-control 1.2.20-1noble.20261006.040504` 및 [공식1.2.20 구현](https://raw.githubusercontent.com/ros-controls/gz_ros2_control/1.2.20/gz_ros2_control/src/gz_system.cpp)이다. 이 backend의 position 입력은 내부 velocity 명령으로 변환되므로 MuJoCo PD/actuator index 판정을 그대로 재사용할 수 없다. 이번 조사는 읽기 전용이며 외부 구현 파일이나 underlay를 수정·복사하지 않았다. 설치된 Gazebo `JointTransmittedWrench`는 joint frame의 원점 기준 wrench이며, 이를 무조건 명령 effort나 MuJoCo actuator_force와 동일시하지 않는다. 실제 native 관측 구현/검증은 별도 G1 항목이다.

- `verify_navigation_13_5.py`의 실제 관절 기하 재구성은 Ch13 자체 `geometry.native_geometry`의 비인접/welded 관계 제외 규칙을 재사용한다(기준 `b26bcfb03e72753140be41e5fa089621f417bd55`). 고정 root URDF에서 관절 값만 대입해 형상 간격을 재검산하며 Python MuJoCo3.3.7 API를 import한다. 외부 구현 파일 복사나 live 엔진의 root/속도 쓰기는 없고 실제 ROS C++3.12.0/Gazebo 물리 인수와 구분한다. 센서 ray/정적 힘/수납/구간 판정과 결함 주입 fixture는 Ch13 신규 코드이며 fixture를 native 출처 증거로 사용하지 않는다.

- navigation 전용 `mujoco_navigation_actuators.yaml`은 원본 `robot_system.xml`의 질량·관성·힘/ctrl/관절 한계를 유지한 별도 생성 모델의 position PD 후보 설정이다. 다리 kp×5/kv×√5 및 팔 kp×1.5·팔/그리퍼 kv×5는 해당 물리 component 비교 UUID와 함께 설정 주석/실행 원장에 기록한다. 기존 description 모델이나 13.4 장면·외부 underlay의 gain을 수정하지 않는다. 새 설정마다 physics/profile hash를 갱신하며 Python component 성공은 실제 ROS MuJoCo/Gazebo의 G1/G2 허가가 아니다.
- `carry_feedback_peer.py`는 시험용 별도 프로세스와 명시적 monotonic-paced `/clock`을 사용하는 Ch13 작성 fixture다. 실제 DDS 액션·watchdog의 통신 경계를 검사하지만 hand-defined joint feedback을 실제 물리 수납/보행 증거로 쓰지 않는다. 호스트 시계나 운영체제 설정을 변경하지 않는다.

- G1 TF 출처 관측기는 설치된 Jazzy C++ `rclcpp::MessageInfo`와 `tf2_msgs`를 include/link하는 Ch13 신규 코드다. Python callback이 GID를 노출하지 않는 사실은 `task8-actual-tf-metadata.json`의 실제 DDS 측정으로 확인했다. 외부 RMW/underlay를 수정하거나 graph의 발행자 수를 메시지 GID로 대체하지 않는다. JSON 직렬화는 설치된 nlohmann_json3.11.3을 사용하며 제3자 구현 파일을 복사하지 않는다. 실제 GID·부모/소유자 전환·출력 수명 시험과 전체 엔진 인수는 별도로 구분한다.

- `carry_manager.py`는 Ch13 `integrated_robot_runtime.arm_action_owner.ArmActionOwner`와 `arm_transport.ArmActionTransport`(재사용 기준 `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`)를 import한다. 예약·지연 acceptance·실제 result 수신·미확정 취소의 소유권 규칙을 복제하거나 외부 원본에 덧대지 않는다. 새 수납/시동/배타 launch와 실제 ROS peer 시험은 Ch13 작성 코드이며, 실제 controller·물리 수납 검증은 G1에서 별도로 수행한다.

- `gait.py`, `crawl_controller.py`, `observations.py`와 관련 수학/실제 DDS·lifecycle 시험은 Ch13 작성 코드다. `observations.py`는 Task5 커밋 `25ba8531f16bb020e5d664df79710b38638c62b4`의 motion_guard 수신 정규화·미래 촬영 inbox를 내부 모듈로 추출했다. 기존 Ch13 `integrated_robot_vision.kinematics`와 ROS 설치 lifecycle API를 import하며 Ch01~Ch12나 외부 구현 소스를 복사하지 않는다. ideal-feedback fixture는 실제 엔진 증거로 사용하지 않는다.

- `projection.py`와 `motion_guard.py`의 새 평면 투영·안전 kernel/수신기/watchdog은 Ch13 작성 코드다. 시각화가 아닌 실제 원본6D odometry의 child-frame 속도 계약은 기존 Ch13 `integrated_robot_vision.native_pose`(기준 commit `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`)와 대조했다. 노드 종료에는 같은 기준의 `integrated_robot_vision.execution.run_node`를 import하며 원본을 복제·수정하지 않는다.

- `integrated_robot_navigation_sensors`의 ABI·소유권 패턴·라이선스와 실제 C++ vendor 버전은 [패키지 출처표](../ros2_ws/src/integrated_robot_navigation_sensors/REUSE_MANIFEST.md)에 기록한다. 외부 고정 underlay 원본은 수정하지 않는다.
- `integrated_robot_navigation/scene.py`의 컵 형상은 Ch13 `scripts/semantic_fixture_13_4.py`, commit `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`에서 필요한 `cup_parts` 형상 구성만 적응했다. 컵 위치를 장면 인수로 바꾸고 평지 접근용 pedestal를 절반 크기0.14×0.18m로 명시했다. 모든 변경은 실제 엔진 형상과 지도에 반영하며 인식 결과를 주입하지 않는다.
- `mujoco_navigation_plugins.yaml`은 같은 commit의 Ch13 `mujoco_snapshot_vision_plugins.yaml`에서 native pose와 기존 snapshot camera 설정을 복사하고 읽기 전용 navigation 센서 항목만 추가했다. 원래 config·카메라 구현은 변경하지 않았다.
- `navigation_bridge.yaml`은 같은 commit의 Ch13 `vision_bridge.yaml`을 기반으로 native scan·IMU·접촉·발 위치·CoM의 단방향 bridge 항목을 추가했다. `/odom`·TF 발행자는 늘리지 않는다.
- 새 `navigation_sensors.xacro`, 장면·접촉 정규화·시험은 Ch13 작성 코드다. [SDF 1.11 lidar 계약](https://github.com/gazebosim/sdformat/blob/sdf14/sdf/1.11/lidar.sdf)의 visibility mask를 사용해 **스캔에서만 로봇을 제외**하고 world 장애물과 RGB 카메라의 로봇 형상은 유지한다.

- 신규 navigation의 샘플·기구학·지지 영역·수납 profile·구간 경계 계산은 새로 작성했다.
  기존 Ch13의 `integrated_robot_vision.kinematics`를 import하며 원본을 복제하지 않는다.
- navigation MJCF는 Ch13 기존 `mujoco/robot_system.xml`(해당 파일 마지막 커밋
  `d45d84eb1e338b1c967f5863c8827cb125187e94`)에서 생성하는 별도 산출물이다.
  외부 checkout이나 Ch01~Ch12 파일을 수정·추가 복사하지 않았다.
- 모델 교정은 navigation 전용 hip 장착 y=±0.13m이며 기존 기본값±0.10m는 유지한다.
  원본 모델의 몸통/허벅지 침투 약20mm와 별도 장착 여유의 근거는 13.5 실행 원장에 기록한다.
- Python MuJoCo3.3.7은 설치된 API 의존성이다. 충돌 검사에는 공식
  [거리 API](https://mujoco.readthedocs.io/en/3.3.7/APIreference/APIfunctions.html#mj-geomdistance)와
  [URDF 확장](https://mujoco.readthedocs.io/en/3.3.7/modeling.html#urdf-extensions)을 참고했으며
  엔진 구현 소스를 복사하지 않았다. 기구학/거리 오프라인 검사를 실제 보행 성공으로 부르지 않는다.
- footprint는 원래 collision을 보존한 구간 경계다. 준비 완료 후의 제한된 gait 관절 구간,
  carry 허용 오차와 몸체 기울기를 포함한다. 팔 전체 작업 공간을 표현하지 않으며,
  향후 제어기는 이 구간 밖의 이동 목표를 거절해야 한다.

13.3 추가: `integrated_robot_interfaces`, `integrated_robot_runtime`, 검증기와 정책
테스트는 새로 작성했다. 13.2 모델/launch 재사용 기준 커밋은
`8d7d7e0b6003845ad7e6ef77420cf35e16758202`이며 원본 파일을 직접 호출한다.
Ch05~Ch12 코드의 추가 복사는 없다. ROS 2 rclpy/message_filters는 설치된 외부
의존성으로 사용하며 그 소스를 패키지에 복사하지 않는다.

## 기준점

- 구현 시작 기준: `1451f54a64374f2ff150a39429cc89e9e3b07696`
- 기준 브랜치 당시 설명: `Merge pull request #15 from silverbjin/feat/ch12-section-12-8-separated`
- Ch05~Ch12는 읽기 전용 참고 자료로만 사용했으며 직접 수정하지 않음.
- 아래 파일을 Ch13으로 그대로 복사하지 않았다. 이름·관절 구성·제어 흐름을 참고해 Ch13용 원시 형상 모델과 테스트를 새로 작성했다.

## 내부 참고 자산

| 참고 자산 | 해당 파일 최종 커밋 | SHA-256 | Ch13 반영 방식 |
|---|---|---|---|
| `Ch05/ros2_ws/src/manipulation_basics/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `1aa1277d230aff744413dc7f390096e9b7164fa8c84d22fe85304b5fac9e97db` | 팔 Xacro 분리와 링크 관성 작성 방식을 참고. 형상·이름은 새로 작성 |
| `Ch06/ros2_ws/src/my_robot_moveit_config/config/ros2_controllers.yaml` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `fb3c3ae27bc2513727ffb3b50da075f9e63d1d88477914b5b63438821139accd` | JointTrajectoryController 구성 관례 참고 |
| `Ch09/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `80f3a865746d3eb58a8a7a72c8395a1b4e1aada6e067ccf8d65863199321305e` | 4족 링크/관절 계층 참고. Ch13은 소문자 정규 이름과 새 원시 형상 사용 |
| `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `0ede255c88a809562b3b66bfc5d84559b8c646157ad3965f4cd32560373e6591` | Gazebo 월드 시스템 구성을 참고해 Ch13 전용 월드 작성 |
| `Ch12/src/quadruped_rl/models/quadruped.xml` | `948718efa81b32708158c67815d8fe6b36aaec43` | `e76c2e9a3eae32e6818063cb0f102901c93c2c094edfb86e1a57c958e5f804e6` | MuJoCo 4족 계층·초기 자세와 위치 액추에이터 의미 참고 |
| `Ch12/src/quadruped_rl/ros_core.py` | `2077fd0b5f7fcaee8c003a9d57b5215253f33f88` | `1a10b04275245d03f4ee77e5c02f47626ee7c4366ca722a566397b76bd4f1f0d` | Ch12.8의 위치 잔차 명령 정책을 확인하는 용도. 코드 복사 없음 |

13.4에서 해시 기준을 **해당 커밋의 Git blob 바이트**로 통일했다. 위 Ch05/06/09 네 값은 이전 checkout 바이트 기준 값을 교정한 것이다. 원본 소스를 수정한 것이 아니다. Windows CRLF와 Git LF를 혼동하지 않는다. Ch12 두 값은 기존 값과 일치했다. 재현 시 checkout의 `sha256sum`만 비교하지 말고 다음처럼 blob을 읽는다.

```bash
git show 2077fd0b5f7fcaee8c003a9d57b5215253f33f88:Ch12/src/quadruped_rl/ros_core.py | sha256sum
git log -1 --format=%H -- Ch12/src/quadruped_rl/ros_core.py
```

## 외부 의존성

| 자산 | 고정 버전/커밋 | 사용 범위 |
|---|---|---|
| `ros-controls/mujoco_ros2_control` | `c261f5552edf124d1000a23fb25b6c07cadeb807` | `MujocoSystemInterface`, 전용 `ros2_control_node` |
| ROS 2 Jazzy `gz_ros2_control` | 설치된 Jazzy 패키지 | `GazeboSimSystem` |
| MuJoCo Python | 3.3.7 | 독립 MJCF 로드/적분 증거 |

기존 하드웨어 인터페이스는 `Ch13/ros2_ws/mujoco_ros2_control.repos`에서 커밋을 고정한다. 후속 승인된 카메라 파생본의 제한된 복사는 아래 소유권 패키지 명세를 따른다. 각 외부 프로젝트의 라이선스는 해당 원본 저장소를 따른다. 현재 상위 저장소에는 루트 라이선스 파일이 없으므로, Ch13 패키지의 `Apache-2.0` 메타데이터를 프로젝트 전체 라이선스 선언으로 확대 해석하지 않는다.

## 13.4 추가 명세

기준은 `df993e86d9b6ad446c058bc3b5a61c59c15495db`(13.3)이며 `feat/ch13-section-13-4`에서 작업했다. 이전 장 파일의 직접 복사는 없다. 다음 Ch07 자료는 개념만 참고했다. `.draft`, `.ok`, 백업, ZIP, 이전 build/install/log를 import하거나 실행하지 않았다. Ch13의 기존 소스는 같은 절 독립 패키지 안에서 확장했으며 외부 장 의존을 추가하지 않았다.

| 원본 경로 | 출처 최종 커밋 | Git-blob SHA-256 | 새 경로 / 변경·참고 범위 |
|---|---|---|---|
| `Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `61466950b6a2200c1810834995eb13e64e73450abc8ef957f8cfe8d580434ef5` | `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/detectors.py`：빨간색 fixture·원본 header 개념 참고. HSV/최대 contour 코드를 복사하지 않고 연결 성분·픽셀 중심 규칙을 새로 작성. YOLO와 별도 backend |
| `Ch07/ros2_ws/src/vision_basics/vision_basics/vision_processor.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `daf09773da3caf9e4ddb7909fc4eb5e7d19c996ee36577c3209c355cba5396b3` | 같은 새 패키지의 `object_detector.py`, `vision_processor.py`：cv_bridge·sensor QoS 참고. 원본 edge 처리와 달리 유계 작업자·RGB-D 정합·시간 계약을 새로 구현 |
| `Ch07/ros2_ws/src/vision_basics/vision_basics/coord_transformer_3_TF_frame.py` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `d0a215c63ff177b206da8670023d6dea192a056e6fe2ebf945e932a7ec8da95f` | 새 패키지의 `geometry.py`, `vision_processor.py`：CameraInfo/깊이/TF 분리 개념 참고. 촬영 시각 TF만 허용, 정합·단위·품질·TTL 추가. 타깃 TF broadcaster는 복사하지 않음 |
| `Ch07/ros2_ws/src/vision_basics/urdf/my_robot.ros2_camera_gazebo.xacro` | `92fa2fea6b61ac04362690341559af21f694a7fc` | `eafada52cb90a99ea3d1d8d6aeaf856d4e17521c24d4d9ca630a3c8705d641a2` | `Ch13/ros2_ws/src/integrated_robot_description/urdf/`와 전용 센서 월드：센서 구성 관례만 참고. 원본 두 자유도 로봇·해상도·프레임을 가져오지 않음 |
| `Ch13/ros2_ws/src/integrated_robot_description/urdf/robot_system.urdf.xacro` | `0872b18f370047b464921d30a84494d968223a4a` | `0e24cb62dc3bcb2a683da92c774d478ed3d65727c204a0b8ca08382b2bacbfc3` | 같은 파일 확장：카메라 pitch -1.5708을 정확한 -π/2로 교정. 장착 위치·물리 질량 유지, vision opt-in 센서/optical frame 추가 |
| `Ch13/ros2_ws/src/integrated_robot_description/mujoco/robot_system.xml` | `0872b18f370047b464921d30a84494d968223a4a` | `9bc986c133e2a1ef3f1c541c952db09c2e66fb272c8d765c59e30ff36fc080a7` | 같은 모델 확장：20 관절/질량 구조 유지, URDF와 동일한 eye-in-hand 카메라 quaternion·센서 추가. 개별 엔진 geometry fixture는 별도 wrapper/world |
| `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/manipulation.py` | `df993e86d9b6ad446c058bc3b5a61c59c15495db` | `d88edc460cf37d85e54df78ce85e91b1606a867935a2ab28ad1f29897aa4dcb4` | 같은 노드 + `arm_action_owner.py`, `tracking_support.py`：stow와 tracking의 단일 세션/미완료 액션 소유권. 물리 pick으로 바꾸지 않음 |
| `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/common.py` | `df993e86d9b6ad446c058bc3b5a61c59c15495db` | `ac85116714f26b3732c4698518ca4a8f9a12b02dd2551875a0e35b3e44b2baa9` | 같은 파일：Jazzy executor 종료 순서·생성자/작업자 종료 처리. 새 vision의 `execution.py`는 별도 single-threaded callback/worker 수명 구현 |

Ch07 `package.xml`은 `TODO: License declaration`이다. 원본에 대한 사용·재배포 권리가 별도로 해결됐다고 주장하지 않는다. 여기서는 구현 본문을 복사하지 않았다. Ch13 패키지는 기존 자체 패키지의 Apache-2.0 메타데이터를 유지한다. 이 표는 라이선스 감사를 대체하지 않으며 상위 저장소 전체의 권리 문제를 해결하지 않는다.

### 13.4 외부 실행 자산

- 기존 ROS/C++ 하드웨어·pose 플러그인은 고정 외부 workspace에서 빌드한다. 외부 checkout은 수정하지 않는다. 카메라 파생본은 아래 소유권 패키지 명세의 예외다. MuJoCo free joint는 선속도가 world, 각속도가 local이라는 설치 버전 계약을 Ch13 adapter에서 처리한다.
- Python 실행 버전은 `Ch13/requirements-vision-13-4.txt`와 각 실제 실행의 versions에 기록한다. CPU PyTorch 2.5.1/torchvision 0.20.1, Ultralytics 8.3.221, OpenCV 4.10.0.84를 사용했다.
- `yolov8n.pt` 출처는 공식 assets v8.3.0이며 SHA-256은 `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`이다. `bus.jpg`는 공식 저장소 v8.3.221이며 `c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63`이다. URL·정확한 크기·권리 관련 원본 선언은 `Ch13/config/vision_assets.json`에 고정했다.
- Ultralytics/model의 AGPL-3.0 또는 별도 Enterprise 조건과 사진 권리는 배포 방식에 따라 별도 확인해야 한다. 본 저장소는 법적 허가를 보증하지 않는다. 모델·버스 원본·해당 주석 영상은 저장소에 넣지 않았다.
- 저장소에 보존한 native RGB/depth/주석 영상은 Ch13의 자체 원시 형상·단색 fixture를 실제 엔진에서 렌더링한 결과다. 합성 정답 영상을 카메라 토픽으로 주입한 것이 아니다.
- 실행 소스 목록/바이트 해시는 각 `source_snapshot.json`이다. 검증기가 생성한 build/install/log/cache/evidence는 소스 인벤토리에서 제외한다. 검증 코드와 최종 문서/evidence 커밋 SHA는 자기 참조를 피하기 위해 구분한다.

## 13.4 후속 디버깅 자산

- `Ch13/scripts/semantic_fixture_13_4.py`: 이 절에서 직접 작성한 속 빈 컵/손잡이/커피/
  탁자 형상 생성 코드. 기존 Ch13의 월드·모델 카메라 설정을 보존하고 실제 native geometry를
  추가한다. 앞 장 소스 복사나 사진 billboard가 아니다. 출발점은 이 저장소
  `cbd967e26d7d47223a6f5adb965e323eb7aee1ff`, 구현 체크포인트는
  `1833497b032c9896f1bf7c0e798abc71a8dbaae6`이다.
- 새 컵 RGB/annotated/depth evidence는 위 자체 형상을 실제 엔진으로 렌더한 결과다.
  외부 모델 가중치는 종전 고정 해시의 로컬 자산이며 Git에 추가하지 않는다.
- 외부 MuJoCo 플러그인은 여전히 `c261f5552edf124d1000a23fb25b6c07cadeb807`,
  수정/재빌드하지 않았다. Ch05–Ch12 소스도 수정하지 않는다.
- `parent_debugger_13_4.py`는 이 절에서 작성한 일반 권한 자식 GDB 진단 도구이며
  native 인수용 production launcher가 아니다. GDB 자체 소스는 복사하지 않았다.
- 아래 소유권 패키지는 설계 및 구현 계획 승인 이후 추가한 제한적 파생본이다.

## 13.4 카메라 snapshot 소유권 패키지

`Ch13/ros2_ws/src/integrated_robot_camera`는 ament_cmake 독립 패키지다.
원본은 ros-controls/mujoco_ros2_control의 고정 커밋
`c261f5552edf124d1000a23fb25b6c07cadeb807`이며, 복사한 파일은 camera_plugin.cpp,
camera_plugin.hpp, LICENSE 세 개뿐이다. 원본 경로·SHA-256·파생 경로·변경점은
[패키지 명세](../ros2_ws/src/integrated_robot_camera/REUSE_MANIFEST.md)에 기록했다.
NASA/United States Government 헤더와 Apache-2.0 원문을 보존했다.

별도 class ID `integrated_robot_camera/SnapshotCameraPlugin`으로 원본을 덮어쓰지 않는다.
두 mjData와 move-only render lease, epoch/reset, 보존되는 polled 요청과 worker 수명은
Ch13 수정이며, mailbox/probe/회귀 테스트는 새로 작성했다. underlay base interface는
복사하지 않고 기존 exported target을 사용한다. 설치 시 configure-time source manifest와
실제 camera/mailbox 두 라이브러리 해시를 감사한다.

추가 통합 수정은 Ch13 Xacro/launch에서 문서화된 `auto_register_cameras=false`를
snapshot 비전 경로에만 전달한다. 별도 class ID를 인식하지 못하는 외부 legacy 자동 등록을
끄기 위한 것으로 외부 소스를 바꾸지 않는다. 기존 upstream/vision=false 경로는 유지한다.
Ch05–Ch12 소스를 추가로 복사하거나 수정하지 않았다.

## 13.4 EGL·종단 계측 갱신 (2026-10-21)

기준은 승인 계획 시작0ff4063f75e2f551aee09349e7fe9454792beea2이며,
실측 런타임 소스는09b057465da50ffcf892c30e2e8f7e9f516ab953에 고정했다.
egl_render_context.hpp/.cpp는 앞서 복사한 c261f55의 EGL 경로를 RAII로 분리한 파생본이며
NASA/United States Government 저작권·Apache-2.0을 보존한다. 새 제3자 소스 복사는 없다.
camera_trace/trace.py/latency_trace_13_4.py·계측 hook·회귀 시험은 Ch13 신규 구현이다.
외부 checkout과 underlay는 clean 고정 커밋 그대로이고 Ch05~Ch12는 수정하지 않았다.
`opengl` rosdep 의존성은 검증된 Ubuntu에서 libgl1-mesa-dev→libglvnd-dev→libegl-dev를 포함한다.
계측은 진단 전용이며 upstream 카메라 기본값·장착 모델·명령 소유권·기한을 바꾸지 않는다.
[원본/파생 기록과 실제 시험](SECTION_13_4_EGL_TRACE_RESULTS_KO.md),
[패키지 상세 출처](../ros2_ws/src/integrated_robot_camera/REUSE_MANIFEST.md)를 참조한다.

## 13.4 종단 인수 보완 (2026-10-21)

이번 보완은 Ch13 내부 Python 노드·시험 실행기·비전 장면·테스트 변경이다.
Ch05~Ch12, 외부 checkout, underlay 및 기존 카메라 파생 C++ 구현은 수정하지 않았다.
새 제3자 소스 파일을 복사하지 않았다.
이 문장은 초기 입력·계측 보완 시점의 기록이다. 이후 서버 경쟁 재현으로 추가한
controller 최소 파생본은 아래 별도 항목을 따른다.

`completion-f8c0bed5/action_boundary.c`는 설치된 Jazzy RCL API를 실제 함수로 전달하는
Ch13 신규 진단 코드다. 설치 헤더를 include/link하며 외부 구현 파일을 복사하거나
교체하지 않는다. shared object와 LD_PRELOAD는 명시적 소유 진단 실행에만 사용했다.
최종 인수의 환경·설치 해시와 이 진단 실행은 별도로 기록한다.
`action_boundary_result_only.c`는 앞선 result4경계 버전의 정확한 원본 바이트를 보존한다
(SHA256 `4eb3907d027a30a6a61cc811780a5846eb512944abf3f5370be3ef0027b29b61`).
`action_boundary.c`의 후속 goal4경계 추가본은 새 compile 로그의 해시로 구분한다.
`arm_transport.py` 및 실제 ROS 격리·수명 회귀는 Ch13 신규 작성으로 외부 구현 복사는 없다.

`clock_load_probe.py`, `render_probe.py`, `gazebo_parent_probe.py`, `collect_final.py`와
실행 workflow도 Ch13 작성 코드다. 고정된 원래 EGL workflow는 출처 경로를 남겨
재사용하며 원본 evidence 파일은 덮어쓰지 않는다. 사용한 ROS/Gazebo API와
소스 대조·한계는 [종단 인수 보고서](SECTION_13_4_COMPLETION_RESULTS_KO.md)에 기록한다.

## 13.4 controller 완료·취소 경쟁 파생본

`integrated_robot_controller`의 [상세 출처](../ros2_ws/src/integrated_robot_controller/REUSE_MANIFEST.md)와
[고정 원본 SHA256](../ros2_ws/src/integrated_robot_controller/UPSTREAM_SOURCES.json)을 참조한다.
JTC4.42.1 cpp/hpp2개와 realtime_tools3.13.0 header1개만 복사했다.
Apache-2.0/BSD-3-Clause 저작권·라이선스를 보존하고 Ch13 namespace/plugin ID로 분리했다.
외부 checkout/underlay 원본은 수정·재설치하지 않았다. trajectory·파라미터 구현은 설치된
공개 API/라이브러리로 재사용하며 복사하지 않는다. C++ 경쟁 재현·유계 프로토콜 worker·
설치/실제 매핑 감사와 회귀는 Ch13 작성 코드다. 비전 외 경로의 기본 controller는 유지한다.

최종 런타임 동결은 `f2fa0eba4c042b00bb70f15b4066869ed370d84f`의167소스/380설치
해시(`completion-f8c0bed5/final-v5/frozen-source.json`)를 따른다. 이후 변경한
`verify_architecture_13_3.py`의 합성 목표 전달 순서와 `test_architecture_probe_time.py`는
Ch13 작성 코드이며 제3자 복사는 없다. 해당 두 파일만의 해시 차이와 원본·설치 동일성은
`legacy-clock-final/frozen-source.json` 및 `after-audit.json`으로 별도 검증한다.

## 13.5 승인된 시계 중계 추가 출처

`integrated_robot_navigation_sensors/control_clock_*`는 Ch13 신규 Apache-2.0 구현이다.
기준 `6be20f7`의 `tf_provenance_main.cpp` exclusive-create/쓰기/파일 수명 패턴을
최소 적응하고 공개 Jazzy `rclcpp`/`rosgraph_msgs`/`std_srvs` API를 사용했다.
외부 코드 복사·앞 장·underlay 변경 없음. 기본 시계를 바꾸지 않는 검증 전용 경계와
실제 시험 상태는 `SECTION_13_5_CONTROL_CLOCK_PROPOSAL_KO.md`에 기록한다.

`integrated_robot_navigation/clock_execution.py`는 Ch13 신규 코드다. 설치 Jazzy
`rclpy/time_source.py`를 읽어 callback 등록 방식을 확인했고, 공개 Node 구독 생성·
topic resolve·callback group/executor API만 사용한다. 외부 소스 복사/수정 및
TimeSource 내부 필드 접근이 없다. 기존 Ch13 `integrated_robot_vision.execution.run_node`
(기준6be20f7)의 constructor/SIGINT/자원 회수 소유자를 import 재사용한다. native
단일 실행기와13.4 원본은 그대로 두고 opt-in13.5 Crawl의 Clock dispatch를 분리한다.
후속 `crawl_controller.py` 센서 메일박스 분리는 같은 Ch13 `SensorInbox`/immutable
`Sample`을 재사용한 신규 코드다. 별도 센서 그룹·메일박스 잠금과 오류 latch를 추가하되
상태 전이/관절 명령 소유자는 하나이며 외부 소스를 추가 복사하지 않았다.

## 13.5 G1 전용 교정 경로

`integrated_robot_navigation/calibration.py`와 전용 경계·통합 시험은 Ch13 신규 코드다.
기준`7f321eb`의 `CrawlMachine`/`Sample`/기존 measured STAND settle을 재사용하고,
G1에서만 실측 lift-return 경로로 분기한다. 일반 CRAWL 곡선/게인, 외부·앞 장 코드는
복사하거나 수정하지 않았다. Python MuJoCo component와 실제 ROS 엔진 인수를 분리해
기록하며, 출처를 숨긴 외부 controller 구현을 새로 포함하지 않는다.

동시수신 판단 경계 수정은 같은Ch13 `SensorInbox`/`Sample`을 재사용한신규코드다.
ROS/wall cutoff선택과동일tick bundle공유를추가하며외부소스복사·receipt/stamp
변환은없다. 원생Gazebo2ms접촉batch는센서패키지자체REUSE에별도로기록했다.

G1의loadedpreconditioning참조함수도동일Ch13로컬신규코드다. 원본heldrest와
측정관절추종압축여유/실측하중을사용하며일반CRAWL이나외부PD게인을복사·수정하지않는다.
기준7f321eb의모델·접촉검증·unload상한을재사용하고원본rest를전처리후에
새로정하지않는다. 명시적FL요청의관절/force인덱스회귀를함께보존한다.

`dispatch_node.py`는Ch13신규코드이며rclpy공개Publisher/SubscriptionEventCallbacks의
`use_default_callbacks`를사용한다. [Jazzy API](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/event_handler.py)를
참조했으나Apache-2.0소스를복사하지않았다. 명시적이벤트컨테이너·메시지QoS는보존하며
기본불일치경고항목만제외한다. 로컬DDS비교와실제메시지/이벤트회귀를물리엔진인수와구분한다.
실제노드계측은Python표준cProfile과공식ROSlaunch prefix/filter를사용하며외부패치를포함하지않는다.

구조재검토참고: `legubiao/quadruped_ros2_control`의Apache-2.0커밋
`5434c5810d1a7fe223bcfd04550e9d3bfdd4b458`,
`controllers/unitree_guide_controller/{README.md,src/UnitreeGuideController.cpp,src/FSM/StateFixedStand.cpp}`.
GitHub API의실제tree SHA와해당고정raw파일을읽기만했다. native단계/소유권구조를
비교했고소스·게인·5종모터인터페이스·시간기반완료조건을복사하지않았다.

relay100 종료 수정은기존Ch13 `integrated_robot_runtime/common.py::DrainingExecutor`를
import해재사용한다. 원본커밋`f2fa0eba4c042b00bb70f15b4066869ed370d84f`,
Apache-2.0이며해당공통파일/외부rclpy는수정하지않았다. worker pool실제join후guard를
해제하는Jazzy호환hook은공통파일한곳의기존private접근으로유지한다.
새실제구독회귀는종료중인콜백이끝나기전guard파괴를재현하고기존13.3프로토콜과함께검증한다.

후속 직렬 navigation 실행기 비교는 설치된 **rclpy7.1.12**, Apache-2.0,
[고정 커밋 bd637294dd02b1c128422395c059fa06df8387a3](https://github.com/ros2/rclpy/tree/bd637294dd02b1c128422395c059fa06df8387a3)의
`experimental/events_executor.py`, native `events_executor.hpp/.cpp`, 공식 pub/sub·service·action
시험을 읽고 설치 API를 호출한다. 외부 SDK 소스 복사·수정·설치 변경은 없다.
`dispatch_node.py`의 MessageInfo signature/tuple 호환 처리와 backend fingerprint는
Ch13 신규 코드다. 원본 메시지·metadata·촬영 header를 보존하며 Serial 역할에만 사용한다.
위의 ‘공통파일 무변경’은 이전 Draining 재사용 단계의 기록이다. 이번 단계에서는
`common.py::spin`에 선택적 executor factory 주입만 추가했다. 기존 기본 분기·종료 절차·
DrainingExecutor 본문은 유지한다. 변경한 runtime과 재사용 vision Python 파일을 실제
설치 bytes와 대조·해시 기록하며, SDK wrapper/extension도 fingerprint한다.
파일 fingerprint와 실제 PID의 mapped-library 증거는 구분한다.

navigation direct Gazebo action의 종료 이벤트는 설치된 Apache-2.0
`ros_gz_sim/launch/gz_sim.launch.py::launch_gz`의 `on_exit_shutdown` 성공 패턴
(`ExecuteProcess(on_exit=Shutdown())`)을 참조한다. 소스 복사/외부 수정 없이 Ch13 action에
공개 API를 호출한다. legacy 13.4 include 경로는 유지한다. 설치 launch 파일 자체의 SHA는
각 native 실행의 `install_manifest.json`에 기록한다. process exit와 launch 이벤트 완료를
구분하며, 부모를 신호 없이 유계 대기하는 Ch13 runner 코드는 신규 작성이다.

- 2026-10-25 G2 movement_decision: Ch13 수신함의 원본 capture/receipt 선택과 기존 movement_snapshot 검증을 재사용. 외부 코드 복사 없음. 기록 타이머와 실시간 결정 시점을 분리하며 200ms 기준·원본 journal은 유지.

- 2026-10-25 일반 CRAWL 중립 착지 후보: libchamp core `8c50f649b3fd28a123beaf6f9618ddfaa1589559`, BSD-3-Clause,
  `leg_controller/leg_controller.h`의 zero_stance/half-stance 개념 및 `trajectory_planner.h`의 중립 중심 궤적을 원문 확인.
  코드/게인/보행 생성기 복사 없음. Ch13 reset 명령 중립발과 기존 travel budget에서 SE(2) 원호 이동을 독립 구현.
  실제 실패 FL calf0.79980582<0.8와 이상적 기존0.45m 재생 성공을 함께 기록하며 native 효과는 아직 미검증.

- 2026-10-25 일반 CRAWL 지지 계획: 기존 Ch13 전체 질량/IK 모델을 실측 CoM에 변화량으로 연결(CoM_actual+CoM_IK(delta)-CoM_IK(0)). 자체 구현/외부 복사 없음. actual4692 fixture·기존1후보/tick/G1 경로를 회귀한다.

- 2026-10-25 G1 return smoothness: Ch13 기존 velocity/acceleration 상한과 자체 quintic blend의 해석 적분을 사용한 제동/복귀 시간 법칙. 외부 코드 복사·새 gain/driver 변경 없음. RED jerk10→관련23PASS; 실제 native 효과는 별도 판별.

- 2026-10-25 native Probe: 기존 Ch13 dispatch_node.NavigationNode / make_navigation_executor / 원본 MessageInfo 어댑터를 재사용(공식 rclpy7.1.12 이벤트 실행기). 외부 코드 복사 없음. 직렬 Probe만 선택하고 일반 node/G2 source는 기존 실행기를 유지. scan_transport는 자체 원본 시각 계측.

- 2026-10-25 명령 순서/중간 정지: `command_order.py`는 실제 로컬 DDS에서 확인한 publication_sequence_number와 원본 MessageInfo를 이용한 Ch13 자체 구현이다. 외부 코드 복사·SDK/시스템 시계 변경 없음. 기존 source epoch cutoff/ROS·wall lease를 유지하고 SYSTEM backstep 후 모호한 RESET/재활성화는 재시작을 요구한다. `g2_sequence.py`는 기존 core의 건강한0속도 pause와 명시 정지 latch를 구분하며 자동 fault 해제를 추가하지 않는다.

- 2026-10-25 일반 CRAWL 간섭 수정: URDF box/cylinder의 보수적 capsule 간격, 자체 2D halfplane 투영·유계 제약 탐색은 Ch13 신규 코드. SciPy는 실패 자세의 오프라인 해 존재 판별에만 썼고 런타임 의존성을 추가하지 않았다. Wang 등 SMC2020 II.D/III(연구 결정 문서의 원문 링크)에서 네 발 지지 몸체 이동/한 발 스윙 분리와 지지·기구학 교집합 원칙만 참고. 논문/외부 코드·형상·게인·스윙높이·발 순서 복사 없음. 실제 성공은 별도 검증한다.

- 2026-10-25 observer 비용 계측: Ch13 기존 Probe/소유 PID 검사에 자체 monotonic/thread CPU·직렬화/쓰기 집계와 bounded slow ring을 추가했다. 외부 코드 복사 없음. 원본 입력/기록·안전 기준·실행기를 변경하지 않는다. 프로세스별 parent CPU는 같은 UID/PGID/start identity 검사를 재사용한다.

### 13.5 G2 관측 기록기 분리

Ch13 자체 구현 EvidenceJournal(Ch13/scripts/probe_navigation_13_5.py). 외부 코드 복사 없음. G2 bounded_history에만 적용하며 JSON 직렬화된 불변 문자열/256레코드·8MiB(in-flight 포함)/한 파일 소유 작업자/비차단 제출/sticky overflow·I/O실패/drain·join 뒤 전량 복원 계약을 적용한다. 기본 G1 동기 기록, 시계·캡처·QoS·유효시간·모터/TF 소유권은 유지한다. 근거: d6715c71 관측 callback 내부 실제 기록 지연과 slow sink RED9.80초. 직접 원인이 확정되지 않은 최초접촉지연 전체가 해결됐다고 주장하지 않는다. 프로파일별 원본 journal과 실제 writer비용·개수·join 보고서를 evidence에 남긴다.

G2 관측 callback 분리는 기존Ch13 integrated_robot_runtime.common.DrainingExecutor(2workers)를 재사용하고rclpy공개MutuallyExclusiveCallbackGroup을이용한다. 입력/clock과frame·native_controls·TF기록그룹분리,Sample참조선택뒤잠금밖deepcopy/JSON직렬화,별도짧은기록잠금. 외부ROS코드복사/수정없음. G1 serialEvents기본과G2실제명령송신기는유지한다. 일반ROS스케줄링설명은공식ros2_documentation/About-Executors를참고하되우선순위/하드실시간보장을주장하지않는다. 고정rclpycommit EventsExecutor 원문웹열기는cachemiss로실패했으므로해당C++소스를이번에재확인했다고쓰지않는다.

공개callback그룹API와스케줄링의일반계약은[ROS2 Jazzy 공식 Executors 문서](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Executors.rst)의Callback groups/Scheduling semantics를확인했다. 서로다른그룹의병행실행가능성을참고했으며Python GIL·운영체제경합을없애거나우선순위/지연상한을보장한다는뜻이아니다. 외부문서/코드복사없음.

후속42c6ad25 실제G2 FAIL로관측기의2-worker pool은최종채택하지않는다. 현재후보는기존Ch13/runtime/arm_transport.py의독립수신노드·동일context·명시적join패턴을참고한G2전용RecordingNode다. 입력NavigationProbe와기록노드가각각기존serialEventsExecutor를소유한다. 기록노드에global launch arguments를상속하지않고use_sim_time=False로두어clock구독은부모의원본하나뿐이다. frame timer는부모ROSClock을직접사용한다. native_controls/TF/frame처리만기록노드에있고그밖의생산/제어소유권은유지한다. 양쪽stop/wake→둘다join→각executor해제→writerdrain/join→전량복원→기록노드먼저destroy를검증한다. 기본G1은sidecar없이기존serial구조다. 코드복사/외부원본수정없음.

후속76473ca6의실제G1 scan신선도실패와동기frame write272.51345ms근거로, 인수runner의G1/G2모두동일유계journal·독립serial기록Node를사용한다. legacy Probe 생성자기본은유지하나실제인수경로는이기본을사용하지않는다. 외부원본/물리/시각/필수기준변경없음.

G1하강후보: d3e89913실제fresh gripper velocity실패의request/brake/return/selectedjoint(보고서두SHA포함)를최소fixture로보존했다. Ch13calibration.py의기존quinticvelocity프로파일을재사용해하강nominal만10mm/s·.1m/s²로낮춘다. 원래20mm/s·.2m/s²상한/상향brake·일반CRAWL/게인·형상·10초·실측인수불변. 외부코드복사없음. 참조회귀와실제물리검증을구분하며공기중속도를낮춘것만으로그리퍼실측성공을주장하지않는다.

헤더전달adapter시계후보: 실제DDSclock유무2PASS11.06초. /clock발행이전혀없는경우에도원본17초123ns의odom/TF/camera_info시각동일,90도회전에서MuJoCo world선속도→child선속도변환동일,원본K/P·정규화R·TF단일발행을확인했다. Ch13description의navigation_enabled일때만MuJoCo pose/camera-info및Gazebo pose adapter use_sim_time=False. V클래스/원본메시지·카메라율/엔진·제어clock은수정하지않았다. navigationfalse의기존13.4simclock설정은유지한다. launch설정RED12.06초와2wirePASS는실제CPU감소/G2완주증거와구분한다.

G1 native 기록위치/실패통신후보는기존Ch13의native-output-g2.py byte-exact copy·원본보존패턴을재사용했다. 외부코드복사없음. G1준비/원본은소유native EXT4에만새UUID로생성하고회수뒤work저장소복사/모든SHA대조. journal256/8MiB한도와sticky FAIL은유지한다. JournalFailure를운전인수실패와ROS정리응답수신의수명으로분리하며오류를성공으로바꾸거나자동재시작하지않는다. 근거58dcbf31실제overflow/272.13ms파일쓰기와cleanup-RPC RED14.14초.

### MuJoCo 시계 전달 비교 확장(사용자 승인, 2026-10-26)

Ch13 자체 `execution_contract.py`에 MuJoCo의 명시적 `relay100/native/native` 검증 조합만 추가한다. Gazebo의 reference/DART 조합과 모든 기본 native 실행은 그대로다. 외부 소스 복사/변경은 없다. 기존 Ch13 C++ relay와 원본값/최초 receipt/소유권/arm/고착 실패 계약을 재사용한다. 새 실행은 새 G1 전체증거와 동일 소스·설치본·물리 SHA를 요구하고 control_clock_contract를 기존 검사에 추가한다. 원본 엔진·관측기 시계와 모든 촬영 헤더·물리/안전 기준은 유지한다. 근거/범위는 SECTION_13_5_MUJOCO_CLOCK_COMPARISON_KO.md, 실패 경계 회귀는 test_mujoco_relay_validation_scope.py다. 실제 성공 주장은 후속 엔진 기록으로만 판단한다.

공식 rclpy bd637294dd02b1c128422395c059fa06df8387a3의 events_executor/events_queue/rcl_support를 GitHub 연결 도구로 읽어 FIFO·take·GIL 경계를 확인했다. 참고만 했으며 코드를 복사하거나 외부 실행기를 수정하지 않았다. 별도 domain219 API 비용 비교 원본 task8-event-api-comparison-56d5c09a-5c0c-4fd1-b1b8-5ae67673269b.json은 엔진 성공 증거가 아니다.

### Crawl guard 상태 수신 경계 수정

Ch13 `crawl_controller.py`의 guard_state 소비자만 RELIABLE KEEP_LAST10→1로 바꾼다. 상태는 현재 lease이며 오래된 명령의 순차 실행 큐가 아니다. 정상/중계 양 경로에서 최신 원본 header·generation·model·고착 fault와 최초 수신 시각을 그대로 보존한다. 시계 역행/미래후보 대기/최초 receipt 만료/200ms 기준/명령 단일 소유권은 바꾸지 않는다. guard 발행자와 관절·접촉·body/IMU/scan 등 물리 원본의 QoS 및 Probe 전량 기록은 그대로다. 외부 코드는 복사하거나 수정하지 않았다.

실제 DDS 유계 callback 정지/10상태 버스트는 기존 코드가 촬영9.970s 최신 상태보다9.700s 오래된 상태를 먼저 전달함을 RED1/12.43초로 재현했다. 최초 수정 관련17PASS/44.08초; native/relay 두 경로와 고착실패·ROS/wall 만료 확장 회귀를 수행한다. 관절 물리 원본을 버려 안전 검사를 통과시키는 변경이 아니다. 첫 실제 MuJoCo f99의 발행 지연/수신 큐 비중은 과거 metadata 부족으로 확정하지 않으며, 새 guard callback에 원본 DDS source/RMW-received/SYSTEM entry를 추가 기록해 구분한다. 이 시각은 진단만 하며 ROS 촬영/monotonic receipt 판정에 대입하지 않는다.

### 13.5 native 참조 원인 분석(2026-10-26)

- 사용자 결정: MuJoCo native 참조 유지·원인 분석만. 제안한 보간 controller는 미채택·미구현.
- readonly 외부 `https://github.com/ros-controls/mujoco_ros2_control`, clean HEAD
  `c261f5552edf124d1000a23fb25b6c07cadeb807`의 hardware write, staging mutex, CM 루프,
  plugin API를 읽었다. 외부 파일/underlay·기존 장은 변경하거나 재빌드하지 않았다.
- 이번 재사용은 진단용 소스 구간 인용이며 새 런타임 코드를 복사하지 않았다. LICENSE SHA256
  `10df721a4406adc5fc3024b9cefc6f62345dda19a28b7d842cc16ee470c6c198` 및 파일별 SHA/줄 번호는
  `analysis-a1ee6678-35ab-484c-9fba-aa861f1af230/result.json`의 external_source에 보존했다.
  이는 사후 소스 대조이고 당시 바이너리와의 재빌드 검증은 아니다.
- 기존 Ch13 model/leg_kinematics/vision.kinematics를 읽기 전용으로 호출해 36개 staged ctrl의
  FK 일관성을 계산했다. 일반 matrix chain으로 교차 확인했고 당시 런타임119파일의 해시가
  현재와 같음을 감사했다. 이를 실제 엔진 성공·명령 적용 시각 증거로 사용하지 않는다.

### 13.5 native 적용 경계 계측 — 2026-10-26 재실행 범위

사용자 재승인에 따라 Ch13 신규 CommandTraceLane/NativeCommandTrace와 pre_step 읽기 전용 hook,
Crawl 발행 기록을 구현했다. 외부 base ABI는 기존 고정 c261f555를 link하며 복사·편집하지 않는다.
CM write의 staged ctrl+과거 snapshot과 실제 physics pre-step의 ctrl+이전step velocity를 분리한다.
pre_step은 ctrl/qpos/qvel을 쓰지 않는다. init에서 고정 수치 공간을 확보하고 별도lane try-lock,
명시적overwrite/drop/내보내기생략 수를 기록한다. JSON·파일 쓰기는 종료 단계의 서비스에서만 한다.
원본 센서/촬영시각·native motor참조·단일owner·물리/인수기준과 기존 전체 Probe 기록은 유지한다.
새 미러 command publisher·보간 controller·외부 원본 변경·ROS시각 재태깅은 없다.

### 13.5 G2 최종 명령 수신 및 fault-held STOP

실제 G2 e75b4e86의 final_command ROS age240ms/receipt182.58ms 실패와 별도 실제DDS RED를
근거로 최종 Twist수신을 model owner/default controlgroup에서 기존sensor group/inbox로 분리했다.
원본 callback-entry ROS/monotonic·DDS발행순서·activation cutoff·generation을 보존한다.
미래/동시수신을 결정cutoff에앞당겨쓰지않으며 유계10개중 적합한원본만선택한다. 오류수신은
고착 플래그만 기록하고 model/final command발행의 판단은기존단일owner에남긴다.

MotionGuard STOP은 fault/generation을그대로둔채 ACK만허용한다. 출력은계속0이고 CRAWL/STAND
재활성화는거절한다. 실제STOPPED·deactivate·action terminal·engine종료는기존판정으로별도확인한다.
외부소스·native모터참조·게인·물리·인수기준을수정하지않았다. 두변경모두Ch13신규수정이다.

### G1 loaded planned return(2026-10-26)

Ch13 InPlaceCalibration만 수정했다. 실제49324eec의접촉뒤기준변화·carry과도응답과실패RED를
근거로 최초고유하중접촉뒤quintic제동을한번수행하고,원래preload까지속도min(.01,2*seek)로
계획복귀한다. 이전계획·접촉원본capture/처리시각·제동·새계획을모두노출한다.
기존jerk envelope를유지하도록짧은ramp의최소기간과짧은거리peak도함께제한한다.
원래10wall초안에1초owner settle여유가없는계획은sticky FAIL이며기한을연장하지않는다.
기존단위시험의2.4초illustration 반복구간만10초내로확장했고물리/3고유/jerk/기한assert는유지했다.
별도seek.002/일반CRAWL/팔·그리퍼목표/native controller/게인/물리/외부원본은변경하지않았다.

### 13.5 관측기의 TF 변환 경계 (2026-10-26)

Ch13의 probe_navigation_13_5.py만 수정했다. 실제d32fdf04에서관측콜백지연171.632ms를기록했고,
설치rclpy7.1.12의원본 bd637294dd02b1c128422395c059fa06df8387a3
events_executor/events_executor.cpp를읽어 take_message가사용자콜백보다먼저변환함을확인했다.
외부소스는복사·변경하지않고public create_subscription(raw=True)/deserialize_message를사용한다.
bounded TF관측은원본바이트/MessageInfo를받고기존GID가있을때만내용을해석한다. GID없는API에서는
기존과같이내용을소유권증명으로쓰지않고필수native C++검사에위임한다. QoS/시각/식별자/관측기준은유지한다.
실제DDS RED뒤36개관련시험이통과했다. 별도CDR인코딩의패딩동일성은보장되지않아시험의비교만
수신payload의촬영·링크·변환값동일성으로교정했고초기실패로그를보존했다. 실제엔진개선은별도확인한다.

### 13.5 관측기 원생 수신 큐 분리 (2026-10-26)

Ch13 probe_navigation_13_5.py의기존RecordingNode/ProbeReceiver/EventsExecutor를재사용해
시계없는ingress node를추가했다. 외부소스복사/수정없음. 원본시계는parent한개,정규화/inbox/전량기록/
촬영·firstreceipt/안전판정은유지한다. 새실제DDS RED14.17→관련25PASS35.68초로main queue의
대기와센서수신을분리하고미완료수신기자원유지/오류고착/전체join을검증했다. 물리합격은별도다.

### 13.5 inbox 잠금 수명과 수신 시각 (2026-10-26)

Ch13 probe_navigation_13_5.py만수정했다. 원래_sample normalization/상태수신/기록함수와동일inbox를
재사용한다. 외부소스/원본헤더/시계/메시지/QoS변경없음. 실제e1696f98 잠금대기로그와두실제DDS RED를
근거로포괄dispatch잠금을없애고firstreceipt를잠금전보존한다. 공유상태교체만각콜백의짧은잠금에서수행한다.
movement_decision의불변참조선택후복사/좌표계산/기록을잠금밖으로옮겼다. 직접22PASS18.26초.
순수callback시험의surrogate에명시적RLock만추가했고기존결과assert는유지했다. 실제엔진재검증은별도다.

### 13.5 종료 진단의 원본 문자열 보존

Ch13 runner의기존native_command_trace응답을그대로복사하며외부소스는변경하지않았다.
대용량JSON변환/구조검사는엔진부모와모든수신기join뒤수행한다. 잘못된원본도버리지않고
최종FAIL로기록하며큐용량/안전/필수검사를유지한다. MuJoCo전용서비스를Gazebo에서요청하지않는다.
기존Gazebo실측ctrl/PositionReference검사는유지한다. 실제서비스내용모방없이원본문자열동일성/
join장벽/손상거부/엔진구분의RED→관련32PASS17.79초를기록했다. 실제정상종료효과는별도검증한다.

### 13.5 불변 관측 기록 후보(2026-10-26)

새 Ch13/scripts/observation_records_13_5.py는 이 프로젝트에서 작성한 코드다. 외부 소스를 복사하지 않았다.
Python 표준 MappingProxyType 및 기존 NumPy 의존성을 사용하며 Sample/정규화/원본 메타데이터를 재사용한다.
probe의 bounded 경로에서만 수신 값을 한 번 고정하고 후속 기록의 반복 깊은 복사를 제거한다.
원본촬영·수신시각, topic/QoS, queue, 전량저널, 원본clock, 물리·제어·인수기준은 유지한다.
실제 ROS 고정배열 scalar 호환 실패도 별도 RED/회귀로 보존한다. 현재 실제 엔진 개선은 미검증이다.

판정 갱신: 위 불변 기록 후보는61개관련회귀를통과했으나비계측전체CPU개선이없어실행경로에서철회했다.
코드/시험은probe-record-cost-66215a66 evidence에보존한다. 현재runtime은원래121/5b84바이트다.
새 OS스레드CPU수집기는 Ch13 작업 helper의 신규 작성이며 외부코드복사/권한상승없다. /proc읽기만한다.

### 13.5 연속 실행 API의 출처

Ch13 probe_navigation_13_5.py의ProbeReceiver만신규수정했다. 외부코드복사없음.
공식ROS2 rclpy7.1.12 고정commit bd637294dd02b1c128422395c059fa06df8387a3의
rclpy/src/rclpy/events_executor/events_executor.cpp(Apache-2.0)을전체읽고public spin/shutdown API계약을확인했다.
https://github.com/ros2/rclpy/blob/bd637294dd02b1c128422395c059fa06df8387a3/rclpy/src/rclpy/events_executor/events_executor.cpp
설치wrapper SHA753cc5da96bbfa154b3a7c263a8596b5a4facaf07d2a4fbbfaa9c81626ef281d,
실제extension SHA53efd7622c109ae6f9ff7ffafc3bffac4856700d39ca51d8689ecaa617a596bd는기존dependency감사와같다.
공식API만사용하며외부원본·C++실행기내부·드라이버·관리자설정수정없음. native callback/시계/안전기준유지.
자식전체정지요청/기한join/자원보존/원본메시지시험과실제엔진검증은별도수행한다.

### 13.5 독립 전량 관측 프로세스

Ch13/scripts/split_observer_13_5.py와기존probe의mission_only경로는이프로젝트의신규코드다.
외부소스복사없음. 공식Python3.12 multiprocessing의spawn/소유Pipe/정상join을사용하며ROS활성스레드를fork하지않는다.
https://docs.python.org/3.12/library/multiprocessing.html
기존NavigationProbe/ProbeReceiver/정규화/frame/원본저널과독립판정을재사용한다. per-recordIPC후보는성능악화로철회했고
그구현·5시험·실패원본은probe-process-cost-72d2eccf에보존한다. 새로운경계는촬영을IPC로중계하지않는다.
고유child의정상종료와hash확인뒤에만자기가작성한private snapshot을읽으며외부파일이나네트워크pickle은읽지않는다.
새모듈도runtime-source manifest에포함하고실제자식의설치모듈경로를부모와대조한다. 물리/안전/원본header/command owner는유지한다.

### 13.5 G1 SHIFT 참조 진행과 실패 결과 분리

gait.py의G1전용SHIFT시간파라미터만원본ROS/wall/기존20ms참조주기의최소진행으로갱신한다.
외부코드복사없음. 실제a50d의컨트롤러발행956/957과native pre-step을출처/SHA가있는
fixtures/native_a50_shift_clock_gap.json에기록했다. 이상적geometry의반례일뿐실제물리재생으로표시하지않는다.
일반CRAWL/native보간/게인/모터/접촉/물리·기존기한/원본capture/receipt는변경하지않는다.
관측기runtime_fault는물리과제FAIL로유지하고정상자원종료와독립표시한다. 새별도프로세스기동측정도원본시각을기록한다.

- G2 7c3373df 이후 일반 SHIFT의 고수준 진행 제한과 시험은 Ch13 자체 구현이다. 외부 소스 복사 없음. 실제 실패의 원본 시각(ROS72ms/wall52.029145ms)을 회귀 입력으로 사용하며, native 모터 보간·물리·게인·센서 header를 변경하지 않는다. 양 엔진 최종 인수는 별도다.

- 2026-10-26 적용 참조 흐름 제어: applied_reference.py, 적용 worker C++ 헤더와
  native_navigation_plugin의 읽기 전용 pre_step echo는 Ch13 자체 구현이다.
  외부 소스 복사 없음. 기본 경로/Gazebo/G1의 credit 미사용을 유지하고,
  명시적 MuJoCo G2만 실제 적용 관측과 정확한 이름·값·원본 ROS/first receipt를
  대조한다. RELIABLE KEEP_LAST1 사건 전송이며200ms 계약·모터 native 참조·게인·
  물리는 그대로다. 단위/실제ROS 시험을 종단 물리 성공으로 간주하지 않는다.

- 접촉 탐색 원본 시간 예산과 접촉 deadline fault 뒤 명시적 안전 착지는 Ch13 자체 구현이다. 외부 복사 없음. 기존 참조/실측/소유권 코드와 stop 경로를 재사용하며 G1·native 모터·물리·게인·모든 수치 인수 기준은 유지한다. 실제 fault 착지 실측은 단위 수학 시험과 구분한다.

- native worker 종료 응답의 소형 원본 저장·두 worker join/계수 대조도 Ch13 자체 구현이다. 단순 서비스 ACK와 engine 종료를 구분하며 외부 복사는 없다. 큰 command trace는 기존대로 수신기·엔진 종료 뒤 검증한다.

### 13.5 CRAWL 직렬 수신 분리 (2026-10-26)
`integrated_robot_navigation/ingress_dispatch.py`는 Ch13 자체 작성 코드다. 기존 공개 rclpy Node/SingleThreadedExecutor API와 Ch13의 worker stop/join 수명 계약을 사용한다. 외부 원본 복사·수정은 없다. guard/sensor/command 원본 콜백과 header/최초 receipt, 기존 TimeSource/제어 소유자·MuJoCo native controller를 유지한다. 참고 이슈/버전/측정 근거는 CRAWL_NAVIGATION_DESIGN과 원본 DDS 진단 evidence에 기록한다. 실제 엔진 성공을 대신하는 자산으로 간주하지 않는다.
- 후속 보완은 기존TimeSource의단일Clock구독·콜백·ROSClock을같은직렬수신노드에배치한다. 공개create/destroy_subscription만위임하며외부rclpy수정/복사·privateTimeSource패치·시각재발행·header변경은없다. 공개해제/재생성·worker한번시작/join을회귀검증한다. 상세판별과원본실패는설계/ledger에보존한다.

### 2026-10-27 MuJoCo 적용 ACK의 촬영 시각 직렬화
Ch13 `native_navigation_plugin.cpp` pre_step의 시각 표현 3개 구문만 고정 외부 `mujoco_ros2_control` c261f5552edf124d1000a23fb25b6c07cadeb807의 `mujoco_ros2_control/src/mujoco_simulation.cpp::MujocoSimulation::publish_clock()`에서 최소 재사용·적응했다. Apache-2.0/미국정부 NASA의2025저작권을 수정 파일과 sensing 패키지 REUSE에 보존하고 LICENSE 전문은 유지한다. 외부 checkout은 clean/읽기 전용이다. 같은 `mjData.time`의 정수초·소수부 절단 표현만 일치시키며, 최신Clock/now/허용오차로 header를 보정하지 않는다. 원본 /clock·모터·기존 관측/카메라/trace는 그대로다. 실제 인수는 새 고정본으로 수행한다.

### 2026-10-27 사전 시각 관측과 상태별 lifecycle 종료
`clock_preflight.py`와 `scripts/check_system_clock_13_5.py`는 자체 작성한 읽기 전용 SYSTEM/MONOTONIC 관측 게이트다. 표준 Python time API만 사용하고 시각·서비스·clocksource를 설정하지 않으며 ROS 수신자/엔진을 만들지 않는다. G1/G2의물리검사나기존runtime역행보호를대체하지않는다. GetState기반종료helper는기존lifecycle_msgs공개API를사용하며외부구현복사·수정이없다. 실측정지와비활성소유권해제는별도필수단계로유지한다. 사전관측선택값·한계·실패원본은설계/ledger에기록한다.

- 2026-10-27: `gait.py`의 제한된 SHIFT-fault hold 정지 관측과 `crawl_controller.py`의 stopped 상태 전달, `test_fault_hold_stop.py`·`test_fault_hold_stop_ros.py`는 Ch13 자체 작성이다. 외부 소스 재사용·외부 원본 수정 없음. 관측은 명령/TF/물리 상태를 변경하지 않으며 기존 실패를 성공으로 전환하지 않는다.
- 2026-10-27: MuJoCo G2 relay100 범위의 원본 ROSClock50Hz 제어/200ms wall watchdog 분리는 Ch13 자체 작성이다. `test_g2_control_cadence_ros.py`의 DDS·정지 입력은 시험 전용이며 실제 엔진 증거로 사용하지 않는다. ROS 2 Clock and Time 설계의 시계 용도 분리를 참고했으며 외부 코드는 복사하지 않았다. 기본/G1/Gazebo·원본 Clock·native 모터 참조는 유지한다.
- 2026-10-27: `gait.py`의 대기 결정 시각/마지막 허용 참조 진행 시각 분리와 두 실패 회귀는 Ch13 자체 작성이다. 기존20ms 상한·원본 safety clock·actual timeout을 유지하며 외부 모터 controller/원본을 변경하지 않는다.
- 2026-10-27: `reference_dispatch.py`·`test_reference_dispatch*.py`와 Clock/ACK 알림 연결은 Ch13 자체 작성이다. 외부 forward controller는 설계 참고로 읽었으며 복사·수정하지 않았다. 원본TimeSource 콜백 후 알림만 연결하고 새구독/worker는없다. 단일모델소유자·양시계20ms명령간격·정확ACK/원래200ms기한·모든물리기준을유지한다. 미래후보보류/DDS깨우기/확인전중복미발행/기한만료회귀는실제엔진증거와구분한다.
- 2026-10-27: ReferenceDispatch의20ms 기준은원본제어판단시작시각으로명시했다. 실제발행시각기준의AppliedReferenceCredit200ms와raw/smoothed실발행간격≥20ms/팔5Hz는변경하지않는다. `test_reference_dispatch_phase_ros.py`의15ms계산은시험전용재현조건이며실제성능증거가아니다. 외부소스복사없음.
- 2026-10-27: `test_reference_due_ros.py`와Crawl의일회성wall기한알림은Ch13자체작성. rclpy공개timer API만사용한다. 원본ROS의진행/데이터age와wall50Hz예약을분리하며미래허용epsilon이나외부코드복사/수정은없다. lifecycle종료시기한알림을취소한다.
- 2026-10-27: 이른 ROS 주기 wake를 예약된 wall 판단 전에 보류하는 `_periodic_control_tick`과 실제ROS 실패 회귀는 Ch13 자체 작성이다. 새 스레드·외부소스·시각 변경은 없고 기존 단일 callback group과 watchdog을 유지한다.
- 2026-10-27: 고정50Hz위상/놓친slot건너뛰기는자체Python구현이다. ROS `rcl` Jazzy commit `18d96c9c2b98e616324ae9a2c7701dd0b0886ff0`, `rcl/src/rcl/timer.c`(blob `7df2d68f0eab8ef15526bbf54655ec1c4e24d0f3`), Apache-2.0/OSRF의예정주기유지개념을참고했다. 외부파일·주석·구현코드를복사하거나외부원본을변경하지않았다. 상세새계약과보존한실패는설계/ledger참조.
- 2026-10-27: `decision_cost_trace`와실제ROS경계회귀는Ch13자체작성이다. monotonic숫자관측만추가하고cProfile·외부라이브러리·새worker를넣지않았다. 거부한시험용프로파일러와실제엔진증거는별도로표시한다.
- 2026-10-27: 적용대기의발행불가IK생략과SHIFT/SWING회귀는자체작성. 측정/phase/STOP검사를유지하고외부코드복사없음. 동일callback의native TID·Python표준thread_time_ns 관측은경과시간과CPU를구분하며실행기/worker/시스템설정을바꾸지않는다.
- 2026-10-27: support.py의고정질량/형상컴파일과parity/cost회귀는자체작성이다. 기존Ch13 `KinematicChain`과질량가중합을재사용하며Pinocchio2.9.2 공식model/data·CoM문서는설계개념만참고했다. 외부파일복사·의존성추가·외부원본수정없음. 이전Ch13 support.py를evidence baseline으로복사(SHA431a426c79f29cdd974f6095d6a8940990f7f48debf169bb7829264bc2847994), 실제상태의비교법/결과와출처를함께보존했다. 센서관절·몸체pose는매번갱신하고물리질량을바꾸지않는다.
- 2026-10-27: MuJoCo G2의단일모델소유자를공개SingleThreadedExecutor로직접실행하는scope와DDS회귀는자체작성이다. 기존독립수신자/원본TimeSource를유지하고외부rclpy원본복사·수정없음. rclpy#1223은다른배포판의유사보고로표시하며이환경의증거로대체하지않는다. 다른역할/G1/Gazebo의실행기선택은유지한다.
- 2026-10-27: `split_observer_13_5.py`의 journal 봉인·종료 후 전체 복원, runner의 partial teardown/실행기 metadata 및 `test_observer_finalization.py`·`test_runner_finalization.py`는 Ch13 자체 작성이다. Python 공식 multiprocessing의 join/소유권 원칙을 참고했으며 외부 구현 복사·의존성 추가는 없다. 기존20초 join·전체 원본/hash/count·모든 신선도/물리 기준을 유지한다. 기존 source2cb4와 실패 원본은 recovery4652fb42에 보존했다.
- 2026-10-27: `observer_journal_13_5.py`와 `test_observer_capture_journal.py`는 Ch13 자체 작성이다. Python 표준 pickle5/struct/io만 사용하며 외부 코드·라이브러리 설치는 없다. 전체 관측기의 증거 계산을 종료 후로 이동하고 원본 capture와 전체 JSON을 보존한다. 실시간 controller/센서 admission은 유지한다. 전체 값 검사로 오히려 느려진39b70e74 후보와 실제 배열·순환 실패도 evidence에 보존했다. 외부 pickle 입력은 지원하지 않는다.
- 2026-10-27: `gait.py`의MuJoCo G2 고수준 `applied_elapsed` 샘플링·scope연결·관련회귀는자체작성이다. 기본/G1/Gazebo의20ms정책과native100Hz controller는유지한다. `test/fixtures/reference-4163.json`은자체실패보고서SHA589518c9의101발행시각offset을추출했으며원본c675/129파일과ZIP1ed0b25b를보존했다. ROS2 Control Jazzy 시간궤적문서는개념참고일뿐외부소스복사·controller교체없음. 단일pending/ACK·속도·200ms·phase기한은기존실측기준으로재검증한다.
- 2026-10-27: 이후실제242efeba의SWING속도실패를근거로시간보정을SHIFT에만한정한 `applied_shift_elapsed`로수정했다. SWING은원래20ms와동일한참조를유지한다. 242원본129/1b50624e·보고서8391540a·ZIPb9bbccbc/2분할을보존했고새회귀는자체작성이다. 외부소스·모터controller·게인·물리기준변경없음.
- 2026-10-28: 공유시계 진단의 C/PowerShell/Python 도구는 자체 작성했고 각 UUID evidence에 실제 방법·원본 표본·SHA를 보존했다. C는 표준 clock_gettime과 읽기 전용 adjtimex(modes=0)만 사용한다. Linux/Microsoft 공식 문서·v6.18 ntp.c는 API/공유커널/명목tick 설명을 확인하는 개념 출처이며 코드 복사·외부 checkout 수정은 없다. 실제 커널·다른 배포판 서비스 변경은 아직 실행하지 않았다. 감사129파일과 진단 원본의 보존본은 clock-blocker-checkpoint-7b3d3197-6ac5-4000-a436-f49bb809321b/checkpoint.zip(SHA3339e3396e06d421953d59dd83aac4082e1cd87f9bb499a37e0ac9fec1a33a04)이다.
- 2026-10-28 후속: 사용자 승인 후 두 서비스/tick수동비교7f639는FAIL·변경복원, 관리영역chrony를유지한서비스전용ef602는시계검사/G1을통과했으나G2의독립grip속도검사에서FAIL했다. 두서비스복원true,현재수동보정/서비스임대없음이다. 자체진단·복원helper/표준libc API만사용했고외부코드·설정·드라이버수정없음이다. N/test/fixtures/reference-095-carry.json은자체실제실패native표본에서출처와SHA를기록해추출한7998bytes데이터다. SHIFT40ms후보·이회귀·표준hashlib/zipfile 기반post-reap저장helper는자체작성이다. native원본은삭제하지않으며각보존본에실제방법소스를포함한다. 기존원본095와ZIP150cc22e/10분할은그대로보존한다.

### 2026-10-28 실행 경계 관측 추가
Ch13 자체 구현인 CrawlMachine에 선택적 고정 단계명 관측 콜백을 추가했다. 실제 MuJoCo G2 relay100의 기존 단일 model 소유자·512개 숫자 ring만 사용한다. model_validate/FK/mass/safety/reference/solve를 원본 wall/threadCPU 경계로 구분하며 새 스레드·외부 코드·모터 보간·시각 재표기는 없다. 관측 유무의 명령/credit/만료 거절 동일성RED13.17초→관련46PASS54.89초다. 기존 ROS 기록의 단계 목록이 추가 관측을 거절한 중간1FAIL/6PASS24.99초도 보존하고 전체 순서 기대를 확장했다. 물리 성공 근거는 아니다. dd4d서비스비교는복원true로종료됐다.


### 2026-10-28 충돌 기하 scalar 산술
외부 코드 복사 없음. Ch13 자체 leg_kinematics.py의 구간별 이차 선분-상자 거리와 URDF capsule 변환을 동일 수식의 고정3원소 산술로 바꿨다. 변경 전 파일SHA ed40a33c00029829bfcf3b4175680ea37bdd3dfe04fa1fced65f304acc8bfe01(HEAD4e87f6f + 당시작업트리)의 자체 NumPy 식을 test/segment_box_reference.py에 동결해 비교 기준으로 보존했다. 불변 URDF 형상·역변환만 bounded cache에 저장하며 실측 관절/몸체/거리/명령은 캐시하지 않는다. 접촉·충돌 크기·마찰·게인·힘상한·native 제어기·시각/인수 기준은 바꾸지 않았다.
고정 Vec3 회귀RED10.46초, 기하/실제PythonMuJoCo 거리16PASS9.44초. CPU기준 비교는수정전43449340 1.139배로목표2배FAIL, 수정후4d52b18d 3.230배PASS다. 이는해당계산의같은q/URDF오프라인비교이며전체실시간성이나실제보행성공이아니다. 회전/오프셋·IK/보행/ROS이웃회귀와새native시험은별도기록한다.


회전·오프셋 URDF360개 자세의 자체 NumPy 기준식 대조, 1,500개 선분·상자·반전, 실제PythonMuJoCo 거리, IK·지지·보행·참조·ROS 관측을 포함한 관련75시험60.18초 PASS다. CPU효과와기하동일성의결과이며native전체성공은미검증이다. 새실제검증을위해이시점의source/설치를동결한다.

## 13.5 순수 질량 계산 후보

`integrated_robot_navigation_sensors/src/mass_kinematics.cpp`와 `integrated_robot_navigation/native_mass.py`는 Ch13 신규 Apache-2.0 구현이다. 기존 Ch13 `_mass_plan`의 불변 질량/기하를 재사용하고 현재 관절값의 산술만 C ABI1로 묶는다. 외부 소스 복사·외부 underlay 수정은 없다. 기존 nlohmann_json은 구성 단계에서만 사용한다. ctypes의 argtypes/restype·CDLL 호출 계약은 [Python 3.12 공식 문서](https://docs.python.org/3.12/library/ctypes.html#ctypes.CDLL)를 확인했다. 기존 질량·관성·물리·궤적·시계·ACK·단일 명령 소유자는 유지한다. 선택 범위·자원 수명은 sensors/REUSE_MANIFEST.md, 수치/수신 비용과 실제 인수 결과는 SECTION_13_5_INGRESS_CAPACITY_KO.md에 연결한다.

### 2026-10-29 G1 엔진별 복귀 정책

Ch13 자체 과거 Gazebo3연속 성공본 `task8-control-clock-af6da055.zip`의 `calibration.py`(HEAD3fd278c6078d2e941a60d07476d7866b2ecea598, SHA3751c16b40dc6fff7fef803f484f309323b3b94e114228f84463d666e9f731f4)의 bounded preload 수식만 현재 Ch13 클래스에 재사용했다. 외부/이전 장 수정이나 코드 복사는 없다. MuJoCo의 기존 loaded quintic 보정을 유지하고 Gazebo에서만 명시적으로 선택한다. 최소 실제 실패 fixture는 native_c1e_gazebo_return_budget.json에 원본 report/source SHA와 시각을 기록했다. 새 물리 성공과 과거 성공은 구분한다.

### 2026-10-29 접촉 노드 종료 수명

Ch13 자체 `integrated_robot_vision/execution.py::run_node`의 deferred SIGINT→callback 완료→executor shutdown→node destroy→ROS shutdown 계약을 `gazebo_contacts.py::main`에 재사용했다. 외부 코드는 복사/수정하지 않았다. rclpy 공식 코드 bd637294dd02b1c128422395c059fa06df8387a3(events_executor.cpp blob3b50f8892f74aa9ccc44aa6979559c9ca6b1e6a4)는 수명 분석 참고이며 Apache2 원본을 Ch13에 복사하지 않는다. 단순 종료3회 정상/제어한 in-flight 콜백 실패/18회귀 및 실제 엔진의 전체 종료 판정을 구분한다.

### 2026-10-29 보행의 유지 참조와 높이 상한 정지

Ch13 기존 activation handoff와 G1 original-preload 복귀의 명령/측정 분리 원칙을 일반 flat CRAWL의 미래 위치 예측·swing 종점에도 적용했다. 외부 코드 복사는 없다. 기존 read-only SHIFT FAULT-stop 관측은 실제bd67d364의 네 발 하중 높이 상한 실패에 한해 재사용하며 새 운동/활성화를 허가하지 않는다. 근거 report SHA2773cf186d1b0767d7b3502390ca5e6b1c8bfe665162843447ec7aff5ec32e32와 원본source afbbe483...는 stance-preload-discriminator-1780e1a3...에 연결한다. 현재 좌표계의 held-q FK를 과거 reset 프리로드와 동일시하지 않는다.


### 2026-10-29 접촉 하중 분배 원리 참고
SEIKO 저자 논문 arXiv2312.16465/공개 SEIKOController.cpp blob0a693326647acc76b79ace97ec8f8f42e7d8b5f6(BSD-2-Clause)을 읽고 위치제어의 힘 분배 원리만 비교했다. 외부 소스·QP·의존성 복사0. Ch13 contact_transfer.py는 자체 작성한 평면 준정적 영공간/수직 컴플라이언스 근사이며 SEIKO 구현 또는 Talos 성능 재현을 주장하지 않는다. 원본URL·수식·한계·실측 판별은 CRAWL_NAVIGATION_DESIGN의2026-10-29 항목에 기록했다.

### 2026-10-29 접촉력 방향 요약과 시나리오 검사

Ch13 기존 gazebo_observation.cpp의 원본 wrench와 충돌 ID를 재사용해 자체 작성한 signed3D 힘 요약을 추가했다. 외부 소스 복사0, 의존성 추가0. 원본/모터/FootContacts 제어·인수 경로는 변경하지 않는다. G2 DART 설정 검사는 기존 자체 함수의 시나리오별 요구 단계만 명시했으며 G1 교정 증명을 보존한다. 근거: 실행 원장4342c86d 항목과 test_dart_contact_runner.py/test_gazebo_observation.cpp의 RED→GREEN.

### 2026-10-29 지지 위치의 유계 하중 분배 계획

자체 작성 contact_transfer.balanced_support_weight는 기존IK/CoM/충돌검사를 콜백으로 재사용하고 세 접촉의 수직 정적 평형으로 유계 후보를 비교한다. 외부 알고리즘·소스·라이선스 코드 복사0, 의존성 추가0. SEIKO의 접촉 힘/위치 제어 구분 원리를 참고했으나 WBC·SEIKO 구현은 아니다. 실제15382b7e 실패자료에서 복사한 test/fixtures/native_15382_support_balance.json은 자체생성자료이며 controller_report SHA를 파일에 기록했다. 해당소스HEAD4e87f6f6031d0ac5e73b2575bcee261e92a0e59e/dirty manifest634dccba8eee687787dc29bfc3e990af24ca64a95a79bc2157617a9f2647b528에 연결한다. 원본수정0. 정지재계획단위시험은미래착지XY를현재발위치에고정하며 원본에없는실제travel accumulator를재현했다고 주장하지 않는다.

### 2026-10-29 후속 발 참조 범위 검사

자체 작성 reference_envelope.py는 Ch13의 기존 ik_leg/thigh_trunk_clearance와 허용된 해제·swing·지지발 보정 범위를 재사용한다. 외부 코드 복사·의존성 추가0. test/fixtures/native_b82a_reference_envelope.json은 자체G2 b82af967의 마지막 안전 명령과 인접 실측의 발췌이며 원본report SHA를기록했다. HEAD4e87f6f6031d0ac5e73b2575bcee261e92a0e59e/dirty manifestd7fd39fffead4f2d8316522e009a8afe0c27e9396d227c6cb4267092d634d870에연결한다. 제약을새로완화하지않고기존제약을후속참조격자에도적용한다. 유한격자의참조기하검사는실제엔진성공·연속공간충돌증명이아니다. 근거d8d0ba2b 판별과 RED14.82초→86GREEN111.37초.

### 2026-10-30 공간 하중 전환 부분 재설계

`contact_equilibrium.py`·`load_transition.py`·`contact_component.py`와 부품 진단 스크립트는 Ch13 자체 작성(Apache-2.0)이다. SEIKO `hucebot/seiko_controller_code@972e3a69af9334eec324e61566433fabf05bf061`(BSD-2-Clause)의 접촉 전환/위치 기반 힘 분배 원리와 Improved Feasible Region `abdelrahman-h-abdalla/jet-leg@73cc3d3fdfa6f4fecb6548e089e16c41c49cde8a`(LGPL-3.0)의 다음 지지 접촉·구동 실행 가능성 원리를 참고했다. 두 저장소의 코드 복사·링크·설치 0건이며 전체 SEIKO/WBC/영역 투영 구현을 주장하지 않는다. 논문·검토 파일·한계는 `SECTION_13_5_CONTACT_CONTROL_REFERENCES_KO.md`와 고정 source-index에 기록했다.

수치 최적화에는 기존 환경의 SciPy 1.11.4를 사용하며 package.xml에 python3-scipy를 선언했다. 외부 checkout/underlay는 수정하지 않는다. FootContacts의 추가 world 벡터/유효 필드는 자체 기존 Gazebo wrench 정규화에서 유도하고 원 촬영 시각을 보존한다. 기존 normal force 판정과 MuJoCo native 참조는 유지한다. 단위·회귀 통과와 실제 엔진 인수는 별도 기록한다.

해석 Jacobian/중력 계산은 Ch13 기존 검증된 Rx/Ry/Ry URDF 기구학에서 자체 유도했으며 외부 코드 복사0이다. 자체 실제 부품26a3a7d1의 첫 입력/모델 fixture는 controller report SHA `f114aea77bc34588bb523e6f4d433f2fc299189eec9133027d0842f2a1b734b0`에 연결한다. 라이브 마감 실패와 CPU 재생 성공은 구분하며 원본 실패를 보존한다.

기존 자체 `native_mass.py`/`mass_kinematics.cpp`의 현재-q FK·질량 모멘트 계획을 접촉 Jacobian·다리 중력에도 공유했다. 고정 외부 코드 복사·설치·수정0이며 sensors/REUSE_MANIFEST에 C ABI와 경계를 기록했다. 근거는 부품b09405c9의 실제 CPU/wall 단계 기록이며 solver 준비 성공을 물리 제어 성공으로 해석하지 않는다. 독립 전체-link FK/기존 질량 회귀와 실제 ROS 구성 선택을 검증하고, 새 실제 인수 전 설치본 감사를 유지한다.

수치 전용 `load_process.py`와 비동기 결과/종료 인수는 자체 작성이다. Python 표준 subprocess/socket/JSON/signal API를 사용하고 외부 코드 복사·새 라이브러리 설치는 없다. 자식의 ROS/명령 권한은 없으며 원본 URDF와 현재 입력만 계산한다. 자기 자식의 정상 stop/ACK/reap·소켓 EOF 수명을 검증하고 그룹 SIGINT는 ROS 부모의 종료 절차로 조율한다. 기본 역할·MuJoCo native 참조·물리 설정은 유지한다. 근거: 실제ce729fb3의 CPU4.50ms/경과13.21ms 및 개선을 보이지 않은 합성 스레드 간격 비교. 합성 비교를 실제 ROS 재현/물리 성공으로 주장하지 않는다.

`load_xyz.py`는 자체 공간 응답/기구학·기존 reference_envelope 검사를 재사용한 Apache-2.0 자체 구현이다. 외부 코드 복사·설치0이다. 선택발XY를 고정하고 지지발XYZ만 허용하며 기존2mm/s/10mm의 벡터 한계를 더 보수적인 L1 다면체로 구현한다. Cholesky 좌표 변환은 같은 엄격 볼록 이차 목적함수와 선형 제약의 조건 개선이며 SEIKO solver 이식이 아니다. 원본 힘 비교와 방법은 task8-load-force-reachability-01/02와 연결하며, 과거 높이 정책의 절대 불가능성 또는 실제 XYZ 하중 성공으로 과장하지 않는다. 고정 자식 정책 확인·원 전송 JSON 소유 복사·취소된 계산 실패 보존·단일 부모 적용/복원도 자체 코드다. Ch01~12·외부 underlay·모터 게인·물리는 수정하지 않는다.

기존 MuJoCo 검증의 _mark_decision_cost 유계 수치 관측을 Gazebo 검증 relay100에도 재사용한다. 자체 CPU/wall 계측이며 외부 profiler/worker/파일쓰기/설정변경을 제어 경로에 추가하지 않는다. direct_model_dispatch·실행기·시계·모터 참조 선택은 유지한다. 근거330b055b의 10초 정착 실패와 세 제어 실험의 불충분한 개선이며, 원인이 규명됐거나 물리 문제가 해결됐다는 주장은 아니다.

`compiled_reference.py`는 Ch13 자체 `leg_kinematics.py`의 Rx/Ry/Ry 역기구학과 capsule/box 거리 계산을 재사용한 Apache-2.0 자체 코드다. 불변 URDF 상수만 준비하고 기존28개 현재/후속 격자를 매 입력마다 재계산한다. 외부 코드 복사·링크·설치0건이다. 독립 기존 `reference_envelope.py`를 비교 기준으로 보존한다. 실제 c3719b6e의 정확한 전송 입력/부모 수신 표본 두 fixture는 자체 생성 report SHA에 연결하며 다른 시각의 q로 대체하지 않는다. 공통 비율 적용은 선형 제약의 볼록성에서 자체 유도하고 비선형 현재 형상을 재검사한다. 물리 성공이나 전체 SEIKO 이식으로 해석하지 않는다.

실제8d4fff0e의8번째 작업 실패를 근거로 위 자체 수식을 `reference_geometry.cpp`의 동기 C++28표본 호출로 옮겼다. `native_reference.py`는 기존 Python 불변 계획·전체 입력 검증을 재사용하고 C ABI 차원·오류·명시적 해제와 부모/자식 바이너리 SHA를 검사한다. reference ABI1은 기존 mass/contact ABI1과 별개다. 두 실제 입력과 독립100자세를 비교하며 Python 기준 경로를 보존한다. 외부 코드/라이선스 복사·추가 라이브러리0이며 수식·형상·게인·마감·물리 인수는 불변이다. native_8d4f_xyz_budget.json은 실제 report SHA와 같은 URDF SHA를 검증하고 불변 limits 출처 fixture SHA를 기록한다. 수치 성공 또는7개 적용을 실제 발 들기/전체G2 성공으로 세지 않는다.

2026-11-01 G1 7057d83b의10초 마감 재발 뒤, 동일 자체 NativeMassEvaluator/NativeReferenceEnvelope를 명시적 Gazebo G1 validation/relay100의 현재 CoM·명목 IK에만 재사용한다. ABI/C++ 코어·외부 원본·MuJoCo·기본 실행·G2 궤적 변경0이다. 명목 IK에는 동일한 현재 참조 격자를 전달하고 원래 호출자의 moving/관절/몸통 간섭 검사를 유지한다. 현재 측정 캐시·fallback·명령 소유자 추가0이며 형상 핸들은 모델 종료에서 닫는다. 근거는 유계 trace의 CoM0.596/IK0.645CPU초 및 같은 실패 입력의 교대48회0.857450→0.227350ms·IK차이0이다. 실제 물리 시간 개선은 별도 검증한다.

QPMAD1.5.1의 최소원본14파일79,301바이트를 sensors/third_party/qpmad에복사했다. 출처 `https://github.com/asherikov/qpmad`, 커밋 `11602ec9f87a62a97ba8318ebd81da6646f3c631`, Apache-2.0/Copyright2017 Alexander Sherikov. LICENSE/NOTICE/헤더표시·blobSHA1/SHA256/고정URL은그대로보존하고 UPSTREAM.json과sensors/REUSE_MANIFEST에기록했다. config.h만고정템플릿으로생성해dense/MPL2-only를선택했다. Eigen은기존시스템의존성이며파일복사0, 외부checkout/underlay변경0이다. 자체 xyz_optimizer.cpp/native_xyz.py는동일12변수/132제약문제를구현하고기존Python SLSQP를독립비교로보존한다. SEIKO전체구현·실제성공을주장하지않는다.

2026-11-01 C1 76b1aac2의실제6초미해제(FL29.5→5.58N)를근거로자체native구성에force_objective를추가했다. 기존rate_1_per_s는독립수치비교기준으로보존하고명시적GZG2자식만bounded_terminal_force를선택한다. 변위결정Rδr[N]의목표를최종힘오차[N]로직접설정하고dt는기존속도제약에유지한다. 기존12변수/132제약·H정규화·32반복·10ms/40ms·28격자·원본모터게인/30Nm/변위/6초는변경하지않는다. 새로운SEIKO코드복사/외부소스변경0이며실측모터토크나과제성공을주장하지않는다. 준비/작업보고서에서선택목적을확인한다.

C1 ComponentCaptureJoiner는Ch13자체구현이다. 외부코드복사/새의존성/ROS발행자/실행기/명령소유자추가0. 같은callback-entry receipt를기존mission SensorInbox와32샘플유계관측결합기에전달한다. 기존40ms전체capture span과촬영/수신각200ms를유지하고접촉을FIFO처리한다. baseline이후미완성접촉만료/overflow/역행은실패를고정하며중간고하중표본을건너뛰지않는다. 원본실패bcec의수신journalSHA를보존하고회귀에는240ms/36수신/74058B만복사했다. 기존ContactTransitionTracker의FK/2N100ms/5mm·기존G2required_checks와모터/물리/힘목적식은변경하지않는다.
# 2026-11-01 보조 기록 수명

`integrated_robot_navigation/clock_witness.py`와 회귀는 자체 읽기 전용 코드다. 원본RAW 조회 전후와 MONOTONIC/REALTIME를512표본 고정 이력으로 평가하며 ROS·시계·드라이버 쓰기를 하지 않는다. 기존150초 수집기는 보존하고 명시적 승인 모드만 실행한다. 외부 소스 복사/새 의존성0이며, 실행 전 소스/설치 바이트를 비교하고 실행UUID에 동일 코드를 고정한다. 자세한 승인·판정 범위는 CLOCK_BLOCKER_DECISION 문서 첫 항목에 있다.

C1의 `observe_contact_cycle`은 Ch13 자체 FIFO 관측 코드이며 원래50Hz/시각/하중 검사를 유지한다. Sensors의 `async_trace.hpp`도 자체 Apache-2.0 구현으로, 고정128개/4MiB 큐와 단일 파일 작업자를 사용한다. 외부 복사·추가 의존성·센서/명령 소유자 추가는 없다. 파일 작업자 정상 drain/join과 fd 수명을 증거로 남기며, 자세한 출처 범위는 Sensors/REUSE_MANIFEST.md에 기록했다.

# 2026-11-01 수신 비용 판별의 추가 기록

`integrated_robot_navigation/ingress_dispatch.py`의 기존 serial Events 경로와 설치 의존성 검증을 Gazebo G2 검증 프로필에도 재사용했다. 외부 소스 복사는 없다. 모델/기본 executor는 유지한다. `runtime_cpu_probe.py`의 고비용 전체 스레드 진단은 기본 비활성·명시 선택으로 한정했다. 원본 RAW bracket과 기존 프로세스/물리 인수는 유지한다. ABBA 합성 비교와 실제 실패의 구분은 `SECTION_13_5_LOAD_TRANSFER_REDESIGN_KO.md` 및 evidence 원장을 따른다.

조기 수집 오류 보고의 현재 작업ID/입력/문맥 연결은 Ch13 자체 수정이며 외부 코드 복사가 없다. QPMAD 반복/허용 오차/수학 모델은 변경하지 않았다. `native_ac904_xyz_iterations.json`은 직전 성공 입력이 섞인 파생 기록으로 scope를 교정했으며 실패61의 정확한 입력으로 인용하지 않는다. box presolve 초안은 작업 폴더에 미선택 상태로 보관하고 runtime/설치본에는 포함하지 않았다.

실행기 단순화는 Ch13의 기존 MuJoCo 직접 실행과 기존 serial Events 수신기를 명시적 Gazebo relay100 G1/G2에 재사용한다. 외부 구현 복사는 없다. 합성 ABBA 모델/수신 비교와 원본 ROS callback-group 문서를 근거로 하며 기본 native 모드·모델/물리/참조 기준은 유지한다. 실제 효과와 설치본 검증은 각 고유 실행 evidence로 구분한다.

## 2026-11-01 L1/box 동등 표현의 재사용 기록

정확한 실패job72를 재현한 뒤 자체 작성 `box_presolve.hpp`를 수치 경계에 연결했다. 기존 QPMAD vendor 원본·커밋은 수정하지 않는다. 행렬의 canonical L1 facet을 증명하고 모두 유지한 상태에서 이미 함의되는 solver 좌표 bounds만 생략하며, 원래132개 행·원래 bounds·기하·토크·32회/10ms는 재검사한다. 자체 CPP6검사·독립 primal/기존 입력/소유권99회귀와 설치 감사를 통과했다. 외부 소스 복사는 없고 SciPy 공식 presolve 문서는 원리 참고다. 위의 '미선택 초안' 문장은 job72 재현 전 기록이며, 실제 물리 효과는 새 고정본 engine evidence로 별도 판정한다.



### 2026-11-01 고정 좌표·Hessian metric 전처리

`integrated_robot_navigation_sensors/include/integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp`는 자체 작성 Apache-2.0 코드다. PlaCo 공식 hard equality elimination, MathWorks 공식 presolve 원리와 고정 QPMAD 원본의 제약 선택 순서를 참고했다. 외부 구현 복사나 vendor 변경은 없다. 원래12차원 목적함수·132행/box를 복원 후 검증하고 한 번의32회/전체10ms를 유지한다. 실제 실패 입력130은 원본 ID/문맥/소스·설치 해시를 검증한50755B fixture로 복사했으며 출처는 `native-contact-component-gazebo-48d02b49-72f1-4248-a4b5-ced23815fcb3/controller_report.json`, 당시 local HEAD `4e87f6f6031d0ac5e73b2575bcee261e92a0e59e` +source manifest `f03259ae…`이다. SHA와 판별 실패/성공은 하중 재설계 문서 및 evidence ledger에 기록했다.


### 2026-11-02 수치 응답 수신 소유권

`integrated_robot_navigation/numeric_receipts.py`는 Ch13 자체 작성 Apache-2.0 코드다. Python 표준 socket/select/threading만 사용하며 외부 소스 복사는 없다. 기존 `load_process.py`의 bounded framer를 단일 reader가 사용하고 최대1개의 완전 응답·최초 MONOTONIC 수신 시각만 보관한다. Gazebo G2에만 명시적으로 선택하며 모델/ROS/모터 권한을 갖지 않는다. 원래40ms·200ms·10ms·32회와 기하·힘·토크 검사는 유지한다. 원인 증거는 `native-contact-component-gazebo-48f565a9-e902-45ae-a0dc-ed878dfc3806`의ID19 및 `job19-transport-2ebde151-01ff-4f80-8a9e-785f4910b5d0.json`, 당시 local HEAD `4e87f6f6031d0ac5e73b2575bcee261e92a0e59e` +원본 소스/설치 해시는 evidence ledger에 기록했다. 기본model_poll 및 MuJoCo/G1은 유지한다.


### 2026-11-02 원래 QP 경계의 수치 표현

자체 작성 `fixed_coordinate_qp.hpp`의 `canonicalize_original_primal`은 원래box 오차1e-9 범위에 이미 포함되던 값만 정확한 경계로 복원하고, 원래 전체 행 residual1e-7과 이후 힘/토크/servo/기하를 다시 증명한다. 부모의엄격한Z비음수조건을유지한다. 외부 코드나 vendor 변경은 없다. 입력57 출처는 `native-contact-component-gazebo-59873b32-4ac9-4451-9950-2175cb256e42`의 원본ID/문맥이며 fixtureSHA `56a7fe61eb589a2da4671e11f4c8cd10b963fb40966a2700bc80a4ae66502053`, 로컬HEAD `4e87f6f6031d0ac5e73b2575bcee261e92a0e59e` +당시소스/설치SHA는evidence ledger에기록했다.
