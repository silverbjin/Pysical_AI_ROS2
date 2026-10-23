# Ch13 13.2 재사용·출처 명세

## 13.5 추가 — 구현 진행 중

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
