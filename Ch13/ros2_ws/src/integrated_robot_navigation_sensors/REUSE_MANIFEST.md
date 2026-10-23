# Ch13 navigation sensing 출처와 경계

이 패키지는 13.5절을 위해 작성한 Apache-2.0 코드다. 외부 checkout과 앞 장 원본은 수정하지 않는다.

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

## 안전·수명 계약

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
