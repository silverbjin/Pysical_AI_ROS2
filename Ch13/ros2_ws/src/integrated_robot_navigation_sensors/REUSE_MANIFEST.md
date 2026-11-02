# Ch13 navigation sensing 출처와 경계

이 패키지는 13.5절을 위해 작성한 Apache-2.0 코드다. 외부 checkout과 앞 장 원본은 수정하지 않는다.

## 2026-10-28: 독립 원본 CDR 관측기

`cdr_journal.hpp`, `navigation_evidence_recorder.cpp`, `test_cdr_journal.cpp`는 Ch13 자체 작성이다. 설치 Jazzy rclcpp28.1.22의 공개 GenericSubscription/SerializedMessage/MessageInfo와 ROS 시계 타이머, 표준 thread/POSIX 파일 API 및 zlib CRC32를 사용한다.
[rosbag2 0.26.11 recorder](https://github.com/ros2/rosbag2/blob/cb8fa198b93bfed90e2417b52b8645fb9ef89c2b/rosbag2_transport/src/rosbag2_transport/recorder.cpp)의 불변 직렬 메시지 수명 원칙을 참고했다. commit `cb8fa198b93bfed90e2417b52b8645fb9ef89c2b`, 파일 blob `d7d3527e19a3a02f9c07901d3197f498cdd50810`, Apache-2.0/OSRF 원본의 코드 복사는 없다.

센서·TF·native 적용 ACK를 직접 수신해 원본 CDR, 첫 MONOTONIC 수신, 별도 SYSTEM/RMW 시각·GID를 기록한다. 새 motor/TF/clock 명령 발행은 없다. 원래 ROS20ms 프레임의 수신 prefix를 보존하고 종료 후 Python의 기존 정규화·SensorInbox로 전체 해석한다. 256레코드/8MiB 큐 초과·기록 실패·부모 손실은 실패를 유지한다. 부모 연결 손실 시에도 drain/join 후 별도 native 종료 보고서를 남긴다. 기존 Python 경로·QoS·주기·원본 시각·안전/인수 기준은 보존하며 `native_cdr`만 명시적으로 선택한다. 독립 ACK 수신을 제어 클라이언트의 수신/credit으로 대신하지 않는다. 실제 엔진 인수는 별도다.

`dart_contact.hpp/.cpp`, `navigation_dart_contact_probe`는 사용자승인2026-10-25의
G1 전용 수치접촉비교를 위한 Ch13 신규코드다(기준checkpoint `3fd278c6078d2e941a60d07476d7866b2ecea598`).
설치 `gz_dartsim_vendor`/DART6.13.2의공개 `ContactConstraint` getter/setter와공식
CMake `dart` target에link한다. [DART6.13.2 API 구현](https://github.com/dartsim/dart/blob/v6.13.2/dart/constraint/ContactConstraint.cpp)은
참조만했고BSD구현파일을복사·수정하지않았다. `dladdr`/canonical경로는실제getter
provider와header버전을대조하며파일/시스템설정을바꾸지않는다.
기본모드는관측만하며setter를호출하지않는다. opt-in만소유한단일world프로세스의
초기0을실제조회한뒤50µm로1회설정한다. 중복소유자·잘못된범위·예상밖초기값은
거부하고reset/retry API를제공하지않는다. 설정값은모든native진단packet에서검증한다.
이설정은기존읽기전용센서와구분된명시적물리설정이며일반CRAWL로자동승격하지않는다.

G1 검증 모드의20ms 연속참조와 `PositionReference`는 Ch13 신규코드다(기준
`7f321ebb4141089a09e06d5c646ac83d180fc906`). 사용자승인에 따라기존 position backend의
다리12관절만 명시적으로 opt-in한다. Gazebo8.15 공개 `Component`/`Factory`/
`VectorDoubleSerializer` API에 link/include하며 외부구현 파일을복사하지 않았다.
별도 Ch13 타입의진단 component는입력/적용참조/기간/실제write시각만저장하며 물리
위치·속도명령 component가아니다. 기존 observer가읽어 기록하고 새명령소유자나
thread를추가하지않는다. 기본모드·팔/그리퍼·게인/감쇠·힘상한은그대로다.
실제엔진/G1전체검증전까지기본보행설정으로승격하지않는다.

`ContactDetailWindow`는 한발 raw 하중상실 edge와 뒤10개 native step의 원본pair/
wrench/깊이·관절상태·실제적용참조를기존batch에보존하는 Ch13 신규진단이다.
장기airborne마다상세량을계속늘리지않고회복만으로새window를열지않는다.
명령/원래contact acceptance/센서stamp·receipt를바꾸지않으며 controller fault를
제어하거나복구하지않는다. 기존raw요약과<3발하중상세기록은유지한다.

| 대상 | 참조·재사용한 출처 | 고정 기준 / 방식 |
|---|---|---|
| 플러그인 base ABI | `mujoco_ros2_control_plugins` | 외부 underlay commit `c261f5552edf124d1000a23fb25b6c07cadeb807`; 헤더에 link, 원본 복사·수정 없음 |
| `SnapshotChannel` / worker | Ch13 `integrated_robot_camera`의 소유권 패턴 | 기준 commit `8e07b05cdf45eeb96dffbfe4fdbe1cf045373146`; 새 구현. 렌더링용 `mjv_copyData`를 복사하지 않고 **전체 `mj_copyData`**와 독립 모델 clone 사용 |
| `navigation_sensor_probe.cpp` | Ch13 `integrated_robot_camera/src/camera_plugin_probe.cpp` | 같은 기준 commit의 pluginlib 로드 검사 패턴을 최소 적응. ROS/GL 초기화 없이 실제 library 경로와 header/runtime version 출력 |
| `LICENSE` | Ch13 camera 패키지 Apache-2.0 전문 | 라이선스 본문 그대로 보존 |
| CMake source manifest | 같은 camera 패키지의 build-time provenance 블록 | 같은 기준 commit에서 sensor 입력 경로에 최소 적응; 빌드 시점 소스와 설치 .so의 출처 대조용 |
| MuJoCo native API | [3.12.0 공식 API](https://mujoco.readthedocs.io/en/3.12.0/APIreference/APIfunctions.html) | 실제 ROS C++ vendor는 3.12.0. 오프라인 Python 3.3.7과 구분. header/library 불일치 시 거절 |
| Gazebo 관측 API | 설치된 gz-sim8 헤더, [Physics.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc), [Contact.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/contact/Contact.cc) | `ContactSensorData` 생성은 관측 요청이며 물리 명령이 아님. 실제 ECM 링크 관성·세계 pose를 읽음. 외부 구현 코드 복사 없음 |
| Gazebo 힘 좌표 계약 | [gz-physics7 GetContacts.hh](https://github.com/gazebosim/gz-physics/blob/gz-physics7/include/gz/physics/GetContacts.hh) | ExtraContactData 힘은 세계 좌표. 접촉 pair 미러링 시 collision 순서와 force 원래 방향을 동일시하지 않음 |
| Gazebo 관절 구동 관측 | 설치된 gz-sim8.15.0 `JointPosition`, `JointVelocity`, `JointVelocityCmd`, `JointForceCmd`, `JointForce`, `JointTransmittedWrench`, `JointAxis` 헤더와 [gz_ros2_control1.2.20](https://github.com/ros-controls/gz_ros2_control/blob/1.2.20/gz_ros2_control/src/gz_system.cpp) | 공개 API를 include한 Ch13 신규 읽기 전용 구현. 외부 코드 복사·수정 없음. 설치 apt는 `1.2.20-1noble.20261006.040504`; position-to-velocity 경로와 read의 joint-frame wrench 투영을 참고하며 무제한 토크/PD 동등성을 가정하지 않음 |
| `gazebo_position_system.cpp` / factory XML | 설치된 `gz_ros2_control::GazeboSimSystemInterface`, `hardware_interface`의 Jazzy ABI와 [1.2.20 resource 초기화](https://github.com/ros-controls/gz_ros2_control/blob/1.2.20/gz_ros2_control/src/gz_ros2_control_plugin.cpp) | Ch13 신규 bounded scalar position PD 후보. 외부 구현 복사·수정 없음. 공식 CMake target `gz_ros2_control::gz_ros2_control-system`의 공개 헤더/ABI에 link. 새 background thread/ROS command publisher 없음 |
| `tf_provenance` | 설치된 Jazzy `rclcpp::MessageInfo`/`tf2_msgs` API, nlohmann_json3.11.3 | Ch13 신규 읽기 전용 관측기. 외부 소스 복사·수정 없음. Python callback에 없는 실제 메시지 GID를 C++ RMW metadata에서 읽고 첫 parent/child/topic/GID 조합을 보존 |

## 순수 질량 모델 산술 후보

`src/mass_kinematics.cpp`는 Ch13 신규 Apache-2.0 구현이다. 기존 Ch13
`integrated_robot_navigation/support.py`의 `_mass_plan`이 만든 불변 질량·고정 변환을
그대로 받아 현재 관절값의 행렬 곱/질량 1차 모멘트 합만 한 번에 계산한다.
외부 구현 복사·모델 교체·질량/관성/충돌/모터 값 쓰기는 없다. 기존 의존성
nlohmann_json은 구성 단계에만 사용하며, 계산에는 ROS·MuJoCo·Gazebo·스레드·시계가 없다.
기하 상한64관절/65모멘트와 원래 유한값·관절 한계·강체 변환 검사를 유지한다.
호출 중 현재 관절/몸체 pose를 캐시하지 않는다. C ABI1의 불변 기하 객체는 Python
소유자가 생성·해제하고, 오류 시 기존 Python 구현으로 자동 재시도하지 않는다.
독립 full-link FK 동등성·수신 부하 비교 뒤에만 명시적 MuJoCo G2 후보로 연결한다.

## 안전·수명 계약

- `control_clock_gate/relay/main`은 승인된13.5 검증 전용 신규 Apache-2.0 구현이다.
  기존 `tf_provenance_main.cpp`(기준6be20f7)의 exclusive 파일/일반 사용자 종료 패턴과
  공개 Jazzy `rclcpp::MessageInfo`, `rosgraph_msgs::Clock`, `std_srvs::Trigger` API를
  참조했다. 외부 소스 복사·underlay 수정 없음. 10ms wall timer는 원본 `/clock`의
  마지막 유효 메시지만 별도 토픽에 복사한다. time 생성·보간·전역 재발행 없음.
  단일 executor가 상태·ROS 자원·trace 파일을 소유하며 source GID/graph 단일성,
  rollback은 항상, 명시적 운전 arm 이후 source 진행200ms 중단은 고착 실패다.
  기존 StartupManager가 실제 센서/claim을 확인하고 다리 활성화 전에 one-shot arm한다.
  arm 자체도 원본 첫 receipt200ms 내의 양의 시각만 허용하고 lease를 갱신하지 않는다.
  bootstrap 때 임의 시간을 만들거나 stale pending 후보를 발행하지 않는다. stop 뒤 재개하지 않으며
  소비자 정리 후 stop/실제 프로세스 exit와 회수를 각각 검증한다.

- schema1 진단의 `body_reference`는 같은 immutable snapshot의 free-root
  `qvel[dofadr+3:dofadr+6]`을 BODY 각속도로 읽는다. gyro `sensordata`를 답으로
  재사용하거나 세계 좌표로 중복 회전하지 않는다. 원생 주소·free root·유한값을
  검사하며 `mj_forward`나 상태 쓰기를 하지 않는다. 검사기는 원본 capture/epoch로
  exact join하고 누락·다른 프레임·축 오류를 거절한다. 비동기 `/odom` 최신값과의
  비교는 같은 촬영의 독립 물리값 검증이 아니므로 MuJoCo 인수에 사용하지 않는다.
  큰 JSON 진단은 양단 RELIABLE/KeepLast100으로 수집한다. 센서·제어 토픽의 QoS는
  바꾸지 않으며 기록 누락은 여전히 인수 실패다. 진단 발행은 기존 worker에 있고
  physics submit의 snapshot mutex를 잡은 채 middleware publish하지 않는다.

- `update`에서 받은 안정된 control snapshot만 읽는다. live 상태 쓰기, root pose/속도 설정, 외력 plugin을 사용하지 않는다.
- worker는 모델 clone과 완전한 데이터 슬롯을 소유한다. 대기 프레임 덮어쓰기는 lease 슬롯을 변경하지 않는다.
- stop은 새 제출·발행을 차단한 다음 worker를 join한다. reset/clock rollback은 이전 frame을 무효화하고 **재시작을 요구**한다. 자동 재활성화하지 않는다.
- stop 서비스의 성공은 worker 정리만 의미한다. 엔진 정상 종료·부모 회수·잔여 없음은 별도 실제 실행 증거가 필요하다.
- MuJoCo scan은 robot group1만 제외하며 world geometry를 유지한다. Gazebo camera visibility는 유지하고 lidar mask1에서만 robot visual group2를 제외한다.
- `/navigation/native_com`의 PoseStamped는 **position에 CoM 점**을 넣는 bridge 공통 운반 형식이다. 로봇 pose나 TF 발행자가 아니다. identity orientation은 의미 없는 운반 값이다.
- ROS `FootContacts`는 odom/world 일치가 선언된 평지 benchmark에서 세계 +z 하중을 N 단위로 보고한다. 임의 경사면·등반 능력이나 실제 G1 센서 정확도 통과를 주장하지 않는다.
- `tf_provenance`는 TF를 재발행하지 않으며 명령·모드 권한이 없다. 동일 authority tuple만 중복 제거하고 부모/발행자/topic 변경은 모두 기록한다. 새 출력 파일만 exclusive-create하며, 수신기 파괴 뒤 파일을 닫는다. 실행 파일 bytes·실제 PID/start tick·부모의 정상 종료 기록은 runner가 별도로 결합한다. graph endpoint 수만으로 TF 메시지 소유자를 추정하지 않는다.
- `/navigation/native_controls`는 같은 소유 snapshot의 실제 `mjData.ctrl`, qpos/qvel, actuator_force/qfrc_actuator와 실제 actuator 설정을 보고하는 schema1 JSON 진단이다. 명령 토픽으로부터 추정하지 않는다. ctrl은 position/other와 hinge/slide 단위를 구별하며 effort 메시지로 위장하지 않는다. 설치된3.12.0 `mjmodel.h`의 nactuator/nu/nout 및 명시 ctrl/output 주소를 사용하고 scalar joint/input/output 이외의 모델은 거절한다. 외부 헤더는 include만 하며 복사·수정하지 않는다. 이 관측 자체는 G1 성공이나 명령 소유권을 부여하지 않는다.

## 검증 해석

`PositionPDSystem`은 관측기가 아닌 **13.5 장면 전용 하드웨어 후보**다. ROS 위치 목표를
actual native q 기반 위치력으로 변환해 원래 `JointAxis.Effort()` 한계로 clamp한
`JointForceCmd`를 쓴다. 감쇠는 모델의 `원래 damping+kv`를 native JointAxis에
명시해 DART의 암시적 적분으로 처리한다. 외부 힘에서 `-kv*qd`를 또 빼지 않는다.
모드·base/native 계수·실제 native axis damping이 다르면 초기화를 거절한다.
ROS cmd position 단위와 내부 힘 단위를 혼동하지 않는다. 이 한계는 **외부 위치력**의
한계이며 원생 수동 감쇠·접촉 wrench를 actuator force로 바꾸지 않는다.
게인은 Ch13 navigation의 기존 `mujoco_navigation_actuators.yaml`을 장면 생성 시
같은 검증된 actuator 모델에서 가져온다. 파일명은 역사적 이름이며 새 값을 복제하지 않는다.
관절 초기화 때 URDF initial_value reset을 한 번만 사용하고 root는 설정하지 않는다.
실행 중 위치/속도 reset·외력·가상 odometry를 쓰지 않는다. 초기/마지막 승인 목표를
비활성 시 감쇠 유지하며 power-off를 흉내 내지 않는다. 잘못된 native 상태/목표/clock
rollback은 sticky fault와 내부 힘0으로 차단하고 자동 복구하지 않는다. 쓰기 핸들은
한 번만 export하며 동일 저장소의 두 번째 쓰기 소유자를 발급하지 않는다.
초기화 seed를 실제 피드백이나 인수 성공으로 세지 않는다. 기존 13.4 기본 하드웨어는
변경하지 않으며 새 물리·profile hash·native G1/G2 검증이 반드시 필요하다.

명시적 PD 후보가 실제 속도 진동으로 실패한 뒤 설치된 DART6.13.2의
`GenericJoint::updateInvProjArtInertiaImplicitDynamic` 공개 헤더/공식
[v6.13.2 구현](https://github.com/dartsim/dart/blob/v6.13.2/dart/dynamics/detail/GenericJoint.hpp)을
참조했다. 외부 구현을 복사하지 않았다. 독립1DoF 실제 DART 실험
`fe875293-b545-44ae-bcd0-7442a7785cb3`은 적분 가설을 판별할 뿐 전체 로봇 검증이 아니다.
Gazebo 감쇠 모델은 변경됐으므로 MuJoCo 포화 PD와 정확히 같은 액추에이터라고 하지 않는다.

Gazebo `/navigation/native_controls`는 schema2이다. 실제 scalar joint ECS의 position,
velocity, velocity/force command와 축·종류·제한, joint-frame 전달 wrench 및 축 투영을
보고한다. `JointForce`가 실제 제공되지 않으면 `applied_generalized_force=null`이며
전달 wrench를 actuator force라고 바꾸거나 zero로 채우지 않는다. 초기 상태/명령이
미준비면 발행을 보류하고, 한 번 제공된 관측이 사라지거나 값이 nonfinite이면
관측기를 fail-closed 한다. 50Hz 기존 관측 주기·stop 수명·명령 소유권은 유지한다.
G1 인수의 native 출처/힘 제한 검증은 별도로 필요하며 진단 발행만으로 승격하지 않는다.

구동 명령은 **Update priority-1**에서 읽는다. 모든 controller PreUpdate가 끝난 뒤이며
기본 priority0 Physics Update가 소비·초기화하기 전이다.
[고정 gz-sim8.15.0 Physics 구현](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/physics/Physics.cc)
의 Update/UpdateSim 순서와 설치된 `System.hh` 계약을 참조했다. 원본 코드 복사 없음.
`sample_phase=pre_physics`, `capture_ns`는 명령 적용 step,
`state_capture_ns=capture_ns-step_ns`는 그 직전 완료된 상태의 시각이다.
ECM q/qd/전달 wrench를 적용 후 상태로 위장하지 않는다. 접촉/CoM은 기존 PostUpdate
관측을 유지한다. 두 단계는 동일 stop mutex를 사용하며 자동 재개하지 않는다.

코어 fixture의 실제 물리 kernel 시험, ROS 플러그인 발행 시험, ECM 시험은 각각 기록한다. 이 시험 통과는 전체 로봇 G1/G2 또는 Nav2 종단 성공을 대체하지 않는다. 실제 엔진 인수는 별도 runner에서 수행한다.

Gazebo 순간 body reference 확장은 Ch13 자체 구현이다. 설치8.15.0의 공개
Model::CanonicalLink/Link::EnableVelocityChecks 계약과 WorldAngularVelocity/WorldPose
component를 사용한다. `EnableVelocityChecks`는 원생 readback 요청이며 속도 setter가
아니다. PostUpdate에서 world→canonical body 회전을 수행하고 기존50Hz 진단에
원본2ms capture batch를 붙인다. gyro/평균 odometry를 복제하지 않는다.
외부 코드 복사·underlay 수정 없음. 원본 의미 비교 출처는
[8.15.0 OdometryPublisher](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/odometry_publisher/OdometryPublisher.cc)와
[8.15.0 Imu](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/imu/Imu.cc)다.

2026-10-24 원생접촉 진단 확장도 Ch13 자체 구현이다(기준HEAD7f321eb).
동일 PostUpdate의 ContactSensorData 원본 pair ID/position/depth/world wrench와
발 collision center를 기존 body reference batch에 첨부한다. 새 ROS 구독이나
제어·접촉 판정·시각 변경은 없다. 빈 pair와 기하학적 바닥 관통을 구분하고,
접촉력을 보간·평균·복구하지 않는다. 기존50Hz 판정은 그대로 유지한다.

후속진단payload는같은2ms원본의발중심/원시pair수/|Fz|합을항상남기되,
raw하중2N이상발이셋미만일때만pair/position/depth/양측wrench상세를첨부한다.
이는진단상세선택용휴리스틱이며ground매핑/중복제거된FootContacts지지판정을
대체하지않는다. 정상구간의상세누락은`details_included=false`로명시하고
기준gyro/원본시각/주기/기존접촉판정은삭제하거나줄이지않았다. 외부복사없음.

2026-10-26 적용 참조 관측은 Ch13 자체 구현이다. 새 applied_reference.hpp는
물리 pre_step의 실제 ctrl을 고정64차원 수치로 try-lock 복사하고, 전용 소유 worker가
sensor_msgs/JointState를 /navigation/applied_reference에 RELIABLE KEEP_LAST1으로
변경 사건마다 발행한다. 원본 적용 시각을 유지하며 CM snapshot/최신시각으로
대체하지 않는다. qpos/qvel/ctrl/외력/물리를 쓰지 않는다. 동일 값의 재태깅 없음,
stop/reset의 자동 재개 없음, worker join·오류·drop/overwrite 계수를 보고한다.
기존 공개 MuJoCo plugin pre_step API와 rclcpp 표준 publisher/thread API를 사용하며
외부 소스 복사나 underlay 변경은 없다. 실제 엔진 G1/G2 인수는 별도다.

## 2026-10-27: 적용 사건 촬영 시각의 원본 Clock 표현 일치

`src/native_navigation_plugin.cpp`의 pre_step ACK 시각 표현 3개 구문은 고정 외부 `mujoco_ros2_control`의 `MujocoSimulation::publish_clock()`을 최소 재사용·적응했다.
- 원본 checkout: `/home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control` (읽기 전용, clean 확인).
- 커밋: `c261f5552edf124d1000a23fb25b6c07cadeb807`.
- 원본 파일: `mujoco_ros2_control/src/mujoco_simulation.cpp`, `publish_clock()` (검토 당시1681~1695행).
- 라이선스: Apache-2.0. 패키지 LICENSE에 전문이 있으며, 수정 파일 상단에 원본 저작권 표시를 보존했다.
- 원본 저작권: Copyright (c) 2025, United States Government, as represented by the Administrator of the National Aeronautics and Space Administration. All rights reserved.
- 변경 이유: 기존 Ch13 ACK의 전체 나노초 반올림은 같은 `mjData.time`을 원본 Clock보다1ns 앞서 표현할 수 있었다. 정수초 floor/소수부 나노초 절단이라는 원본 표현만 일치시킨다. 현재시각·최신Clock을 읽지 않고 같은 pre_step capture에서만 계산한다. 외부 원본·실제 /clock·카메라·기존 sensor/trace header는 바꾸지 않는다.
- 기존의 ‘외부 복사 없음’ 기록은 최초 worker 구현을 설명한다. 이 추가분에는 위 원본 최소 구문을 명시적으로 재사용한다. 실제 물리·게인·controller·미래거부·모든 인수 기준은 유지한다. 단독 해결 및 실제 G1/G2 성공은 별도 재검증한다.
# 2026-10-28 control clock receipt/publication boundary

The clock deadline anchor and bounded input/publication records are Ch13-owned
code. The preserved pre-change source is tied to native G2 `22afb6c3`, source
manifest `34a8e9412255b67ea601eec208a9d0ddb2b497e15de03e0573ba808c38618297`.
`ros-tooling/topic_tools` 1.3.4, commit
`462af78b06ad8baafc27ce09cb3dfee96421cfab`, Apache-2.0, was reviewed as a
rate-limited forwarding reference; no external source was copied. Ch13 retains
its original clock objects, sticky faults, owner checks and 100Hz ceiling.
RAW/SYSTEM/MONOTONIC observations are separate diagnostic domains. Publication
and receipt records are emitted after closing the gate; no input file I/O or
new callback worker is introduced.

## 2026-10-30 공간 접촉 기구학의 컴파일 계산 재사용

자체 `mass_kinematics.cpp`의 현재-q FK·고정 질량 모멘트 집계를 접촉 Jacobian과 다리 중력 effort에도 공유한다. 기존 mass C ABI1은 유지하고 별도 contact ABI1을 추가한다. 자체 Python `contact_equilibrium.leg_terms`와 독립 무작위 자세/원본 실제 입력으로 비교한다. 외부 코드/라이선스 소스 복사·의존성 추가0. 모델/현재 관절/강체 자세/접촉점/핸들 수명을 검증하며 ROS·엔진·시각·명령 쓰기·worker·측정 캐시는 없다. CRAWL 명령 권한과 모든 물리/마감 인수는 기존 소유자가 판단한다. 근거는 실제 부품 b09405c9의 공간 응답 CPU7.3429ms이며 solver 초기화만으로 실패가 해결되지 않은 기록을 보존한다.

## 2026-10-30 현재·미래 참조 형상의 C++ 일괄 계산

`reference_geometry.cpp`와 navigation의 `native_reference.py`는 Ch13 자체 Apache-2.0 코드다. 기존 자체 `compiled_reference.py`/`leg_kinematics.py`의 Rx/Ry/Ry 역기구학·정확 FK 잔차·piecewise quadratic capsule/box 거리를 같은28표본으로 옮겼다. 별도 reference C ABI1이며 기존 mass/contact ABI는 불변이다. 불변 형상 계획만 소유하고 현재 입력·배열 차원·유한성·IK 오류·핸들 수명을 검사한다. 실패 시 출력은 확정하지 않고 Python 대체 계산이나 자동 재시도는 없다. 외부 코드 복사/추가 라이브러리0, ROS·시각·측정 캐시·명령 쓰기0. 근거는 실제8d4fff0e의8번째 작업 CPU7.902/경과10.8885ms이며 검사 표본·10ms 기준은 유지한다.
부모/수치 자식은 같은 reference 라이브러리 SHA를 준비 응답에서 대조한다. 자식의 정상 종료 ACK 전 형상 핸들을 명시적으로 해제하고, 부모도 수치 소유자 종료 뒤 자신의 동기 핸들을 해제한다. 정상 프로세스 회수를 물리 성공으로 바꾸지 않는다.

## 2026-11-01 현재 공간 QP의 native 계산

`src/xyz_optimizer.cpp`와 navigation의 `native_xyz.py`는 Ch13 자체 Apache-2.0 구현이다. 기존 자체 `load_xyz.py`의12변수/132선형 제약·동일 정규화 이차 목적·공간 응답을 C++로 옮긴다. 기존 mass/contact/reference ABI는 불변이고 별도 XYZ ABI1이다. 현재 입력만 계산하며 수치 workspace 외에 이전 관측/해를 다음 계산의 warmstart로 사용하지 않는다.10ms/32반복·독립 잔차·정확 후속 기하·명령 소유권은 유지하고 fallback/자동재시도·ROS/엔진 제어는 없다.

- QP 의존성: [asherikov/qpmad](https://github.com/asherikov/qpmad),1.5.1, 커밋 `11602ec9f87a62a97ba8318ebd81da6646f3c631`, Apache-2.0.
- 저작권: Copyright2017 Alexander Sherikov. 원본 `LICENSE`/`NOTICE` 및 각 헤더 표시를 그대로 보존한다.
- 최소복사: `third_party/qpmad/`의 원본 runtime헤더/템플릿·LICENSE·NOTICE14파일79,301바이트. 테스트/benchmark/빌드 시스템/`testing.h`는 복사하지 않았다. 모든 blobSHA1·SHA256·URL은 `UPSTREAM.json`에 있고 원본바이트를검증했다. 기존외부checkout/underlay 수정0.
- `config.h`만 고정 `config.h.in`에서 생성한다. tracing/householder는끄고 `QPMAD_PEDANTIC_LICENSE`로 Eigen의 MPL2-only dense 경로를 사용한다. 원본 헤더 수정0. Eigen은 기존 시스템 패키지에 의존하며 헤더를 복사하지 않는다. 라이브러리와LICENSE/NOTICE/UPSTREAM메타데이터를 함께 설치한다.
- [공식 라이선스 선택 근거](https://github.com/asherikov/qpmad/issues/9)는 dense/MPL2-only 범위를 확인하는 데 사용했다. 사용하지 않는 sparse 기능이나 전체 SEIKO/WBC 이식을 주장하지 않는다.

근거는 실제141b0434의 solver경과12.542/CPU4.456ms, 실제1스레드, 코어 분리 합성비교의 개선 부재다. native 구현·수치 비교를 실제 보행 인수 성공으로 해석하지 않는다.

2026-11-01 C1 76b1aac2의실제6초미해제(FL29.5→5.58N)를근거로자체native구성에force_objective를추가했다. 기존rate_1_per_s는독립수치비교기준으로보존하고명시적GZG2자식만bounded_terminal_force를선택한다. 변위결정Rδr[N]의목표를최종힘오차[N]로직접설정하고dt는기존속도제약에유지한다. 기존12변수/132제약·H정규화·32반복·10ms/40ms·28격자·원본모터게인/30Nm/변위/6초는변경하지않는다. 새로운SEIKO코드복사/외부소스변경0이며실측모터토크나과제성공을주장하지않는다. 준비/작업보고서에서선택목적을확인한다.

## 2026-11-01 시계 중계의 보조 파일 기록 분리

`include/.../async_trace.hpp` 및 관련 시험은 Ch13 자체 Apache-2.0 코드다. 기존 std::thread/condition_variable/nlohmann_json만 사용하며 외부 복사·의존성 추가는 없다. G1 8500b070에서 시계 trace 처리216.189ms 동안 최신 센서가 수신되지만 제어 시계는19.210초에 머물렀다. 이 경과에는 스케줄링이 포함될 수 있어 정확한 write syscall 시간·디스크 단독 원인으로 단정하지 않는다. 시계 executor에는 유계 직렬화/큐 제출만 남기고 파일 쓰기는 단일 작업자로 분리한다. 미기록/in-flight 합128개·4MiB 고정 상한, FIFO, 초과·쓰기 실패는 terminal 오류, 무시/재시도/덮어쓰기 없음. ROS/물리/TF/명령/시각 쓰기 권한은 작업자에게 없다. 원래 relay close 뒤 drain/join, 그 뒤에만 fd를 닫으며 실제 writer witness와 모든 기존 종료·시각 기준을 함께 요구한다.

`observer_cost.hpp`는 후속 G1 05379a5f의 전체 처리량 저하를 판별할 자체 유계 계측이다. 기존 observer mutex 안에서 Update/PostUpdate의 경과·스레드CPU 합계/최대와 두 단계 사이 경과만 고정 크기로 집계한다. 이미 있는50Hz native_controls packet에 이전 완료 callback의 누적값만 추가하며, 센서/명령/header/물리/인수에 사용하지 않는다. 별도 이력/파일/worker/외부 소스/의존성0이다. 단계 사이 경과를 DART CPU 비용으로 단정하지 않고, 오류 카운터가 있으면 성능 증거로 사용하지 않는다. 이 계측 자체는 보행 실패의 해결이나 인수 성공이 아니다.

## 2026-11-01 관측 snapshot 직접 전달

실제 C1 7e642180에서 수치 계산 CPU3.4507ms/경과10.4469ms였고, 같은 물리 구간의 Ch13 observer Update/PostUpdate는 스텝당CPU451.10µs/경과494.03µs였다. `gazebo_observation.cpp`의 기존 검증/스키마를 자체 JSON 값 snapshot API로 공유하고, 기존 StringMsg API는 같은 값을 인코딩하는 호환 wrapper로 유지한다. 엔진 내부는 문자열 dump/parse 왕복을 제거하고 완료된 body batch의 소유권을 move한다. ECM 참조·포인터를 callback 밖으로 공유하지 않는다. 기존 scalar/frame/time/command-null/force 부호/NaN 거절과 모든 빈 접촉 표본을 유지한다. 관측 횟수·2ms/50Hz·전달할 관측값·모터·물리·10ms/32회·40ms·모든 인수 기준은 불변이다. 외부 코드/의존성/worker 추가0이며 micro CPU 비교는 실제 엔진 성공을 대체하지 않는다.

## 2026-11-01 접촉·QP·28표본 기하의 단일 호출

실제 C1 9c62136f에서도 전체10.5811ms/스레드CPU3.6444ms로 탈락했다. 관측 JSON 개선만으로 해결되지 않아 Ch13 자체 `ch13_xyz_complete_evaluate` ABI1과 `native_complete_xyz.py`를 추가한다. 기존 contact ABI1→동일 XYZ ABI1(QPMAD1.5.1,12변수/132제약)→기존 reference ABI1(28표본)→정확 servo 제약을 C++에서 연결한다. 같은 라이브러리를 링크하며 외부 소스·헤더 변경/의존성 추가0이다. Python은 재사용 버퍼를 소유하고 기존10ms 시작 시점부터 남은 예산만 전달한다. 출력은 모든 검증 후에만 확정하며 부모만 명령을 발행한다. 일반 affine 역행렬을 유지하고 rigid transpose로 대체하지 않는다. 기존 분리 경로와 독립 primal 검사를 회귀 기준으로 보존한다. 10ms/32회/40ms·모든 물리·미래 기하 기준을 유지하고 캐시·warmstart·fallback·재시도·권한 추가는 없다. 새 ABI의 출력/핸들/준비·종료 계약은 별도로 검증하며 실제 엔진 성공은 아직 주장하지 않는다.
## Ch13 strict box implication presolve (2026-11-01)

Own code `include/integrated_robot_navigation_sensors/box_presolve.hpp` and its tests; no external source copied. The fixed QPMAD upstream headers/commit remain unchanged. Analytically box-implied rows may be omitted from the solver with a conservative floating-point guard; the original12 variables, box, objective,132-row post-validation,32 iterations and10ms cap remain. Based on the standard presolve principle documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html); this is an independently written bounded QP adapter, not SciPy code. Exact failed job72 from C1 `4d26fb83` is bound by matching request/input/reply IDs before replay. Original failed evidence is preserved.

# Ch13 고정 좌표 전처리 추가 기록 (2026-11-01)

2026-11-02 추가 `include/integrated_robot_navigation_sensors/inverse_remainder.hpp`는
자체 작성 Apache-2.0 코드다. 기존3관절 다리의 삼각함수 FK Hessian 전역 상한과
Jacobian 역함수의 수축 조건으로 보수적인 servo 선형 제약 여유를 직접 유도한다.
임의 토크 여유나 한도 상향이 아니며, 실제 IK가 증명된 반경에 속하는지와 원래
비선형 토크 상한을 모두 후검증한다. SEIKO 공식 논문/저장소의 위치 제어 기반
힘/토크 제약 통합 구조를 참고했으나 이 나머지 경계식이나 외부 구현을 복사하지 않았다.

`include/integrated_robot_navigation_sensors/fixed_coordinate_qp.hpp`와
`test/test_box_presolve.cpp` 추가 증명은 Ch13 자체 작성 Apache-2.0 코드다.
PlaCo 공식 hard equality elimination 및 MathWorks 공식 presolve/postsolve의
표준 치환 원리만 참고했고 외부 구현은 복사하지 않았다. 원래12차원 해를
복원해 모든 원래 제약을 재검사한다. 같은 자체 작성 헤더에 추가된
`equilibrate_all_constraints`는 모든 finite bounds를 일반 행에 포함하고
양의 Hessian metric으로 행을 스케일한다. Eigen 기존 LLT API만 사용하며
QPMAD 고정 vendor/라이선스는 그대로다.

같은 자체 작성 헤더의 `canonicalize_original_primal`은 원래 normalized box
오차1e-9 이내에서만 정확한 경계값을 복원하고, 원래 전체 행 residual1e-7을
다시 검사한다. 이후 모든 힘/토크/servo/기하 증명은 복원된 값으로 수행한다.
부모의 엄격한 비음수 조건을 완화하거나 유의미한 위반을 보정하지 않는다.


## 2026-11-02 independent discrete-equilibrium arithmetic

`src/equilibrium.cpp` is original Ch13 Apache-2.0 energy/Jacobian arithmetic,
with existing Eigen/nlohmann dependencies only. No DART/ROS implementation was
copied. It evaluates URDF full inertia, gravity, sphere-plane contact Jacobians,
implicit native damping and fixed PD saturation. The derivative is formed from
the complete equilibrium equation, including geometry and gravity derivatives;
it is neither symmetrized nor multiplied by an empirical coefficient. The exact
saturation boundary, nonpositive inertia, singular systems, nonfinite values and
linear residual errors are rejected. This library alone has no motor authority
and is not enabled in the crawl runtime until independent regressions pass.
Official model semantics: https://github.com/dartsim/dart/blob/v6.13.2/dart/dynamics/detail/GenericJoint.hpp
and https://github.com/dartsim/dart/blob/v6.13.2/dart/simulation/World.cpp .

## 2026-11-02 explicit Gazebo discrete complete path

`xyz_optimizer.cpp` optionally owns the new equilibrium plan for explicit
`gazebo_discrete_equilibrium_v1` only. The default spring/132-row path and
existing ABIs remain. The complete call includes all current20 q and command
values, uses the command IK Jacobian to map12 XYZ inputs, and includes measured
posture response in the20-axis PD effort derivative. The discrete path has148
rows: original physical torque/force/friction/rate/offset conditions plus all20
predicted actuator effort caps. Every row is postchecked; fixed-coordinate,
QPMAD1.5.1 upstream,32-iteration and total10ms checks remain. The original
28-point geometry/IK branch proof remains. At a clipped actuator the derivative
is zero, matching the installed PD clamp. Raw preclip P is retained as a tracking
diagnostic and is not represented as measured output torque. Actual hardware
clamping and its20/30Nm leg caps are unchanged. This local quasistatic predictor
is not an exact transient or full-path proof; measured release remains required.
No worker, cache, warmstart, fallback, retry or command owner was added.
