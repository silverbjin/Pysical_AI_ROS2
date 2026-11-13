# Ch07 §7.2 — 실제 Gazebo OGRE2 RGB-D 이미지 발행 복구 인수 보고 (2026-11-13)

> **2026-11-13 갱신:** Issue #127의 **원본 Gazebo RGB Image + CameraInfo + optical TF** 미발행 문제가 원인 분석·소스 수정·공개 CI 실측으로 해결되었다. 기존 2026-10-20 정적 리뷰는 아래에 역사 기록으로 보존한다. **전체 RGB-D Depth 정렬, GUI 및 Pick-and-Place 인수가 완료된 것은 아니다.**

## 1. 정확히 확정한 원인

1. 최초 Headless와 Xvfb 실행 [#43219759351](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43219759351), [#43220866643](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43220866643)은 RGB Image=0, CameraInfo=0, `CreateMaterialImpl`/메모리 오류로 중단했다.
2. 공식 `--headless-rendering`만 도입한 최초 [CI #43438209192](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43438209192)에서도 0/0과 OGRE2 `ItemIdentityException: HLMS Datablock '[Hash 0x64f0b670]' already exists`를 재현했다.
3. 원본 `my_robot.ros2_camera_gazebo.xacro`의 RGB-D sensor 내부에 `gz-sim-sensors-system`이 선언되어 있었고, CI 월드 `ch07_camera_world.sdf`에도 같은 시스템이 있었다. 실제 `gzserver.log`에서 각각 엔티티 1과 33에 `Sensors`가 한 번씩, 렌더 스레드가 2개 로드된 사실을 확인했다. **중복 센서 시스템이 같은 렌더링 자료구조를 초기화해 충돌**한 것이 본 결함이다.
4. 유사 사례: [gz-sensors #497](https://github.com/gazebosim/gz-sensors/issues/497), [Gazebo Harmonic 공식 센서 문서](https://gazebosim.org/docs/harmonic/sensors/). **월드 레벨에 `Sensors` 하나만 유지**하는 공식 구조를 적용했다.
5. 원본 Image·CameraInfo의 `frame_id=my_robot/link_wrist/rgbd_camera`는 실제 `/tf_static`의 `camera_optical_frame`과 연결되지 않았다. Harmonic의 `<gz_frame_id>camera_optical_frame</gz_frame_id>`를 추가해 이미지·CameraInfo·실제 Optical TF 이름을 맞췄다.

## 2. 적용한 최소 소스 수정

- `Ch07/ros2_ws/src/vision_basics/urdf/my_robot.ros2_camera_gazebo.xacro`: RGB-D sensor 내부의 **중복 Sensors 시스템 플러그인만 제거**하고 기존 RGB-D 센서·카메라 사양·관절·기구학·OGRE2를 유지, `gz_frame_id`만 추가했다.
- `ci/docker/ch07_camera_once.sh`: Xvfb/일반 `-s` 대신 공식 `gz sim -s -r -v 4 --headless-rendering`을 사용한다. Bash 중첩 반복 변수 충돌을 제거하고, `setsid` 프로세스 그룹 회수 및 최종 종료코드를 실제 정리 후 기록한다.
- Gazebo Harmonic이 SIGINT 시 간헐적 교착을 일으키는 문제 [gz-sim #4173](https://github.com/gazebosim/gz-sim/issues/4173)를 회피하기 위해 `--iterations 12000`으로 유한한 시뮬레이션을 실행하고 자연 종료한다. 일반 `/server_control stop: true` 호출만으로는 살아 있는 Ruby Gazebo 프로세스를 종료하지 못했던 원본 로그를 보존한다.
- `ci/docker/verify_camera.py`: **실제** ROS Image 3개 이상, 640×480 rgb8/bgr8, 타임스탬프 3개 이상, 실제 CameraInfo 양의 fx/fy 및 `camera_optical_frame` 일치, 독립 `/tf_static` 확인을 요구한다.
- 베이스 GHCR Docker **고정 digest `sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f` 그대로**, 새로운 이미지 빌드나 Ch11 기존 합격 시험 반복 없음. Ch10 HOLD 유지.

## 3. 실제 최종 CI 인수 판정

- [**최종 공개 CI #43441463628**](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43441463628) **SUCCESS**, [원본 Artifact #14045524144](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43441463628/artifacts/14045524144).
- `CH07_127_SINGLE_WORLD_SENSORS_STATIC_CONTRACT_PASS` 및 `CH07_127_EXACTLY_ONE_RUNTIME_SENSORS_SYSTEM_PASS`: 세계 Sensors=1, 로봇 Sensors=0, 원본 RGB-D sensor=1.
- `BOOK_CH07_CAMERA_PASS`: 실제 Image **3건**, CameraInfo **3건**, optical TF **1건**.
- RGB 예시: **640×480 rgb8**, 실제 버퍼 **921,600 byte**, `frame_id=camera_optical_frame`, timestamp **2.707초**(시뮬레이션 시간). 실제 K `fx=fy=554.3827128226441`.
- `image_camera_info_optical_tf_frame_consistent=true`, `unique_valid_image_timestamps=3`, Gazebo OGRE2 렌더 스레드 정상 시작·종료.
- `GAZEBO_NATURAL_ITERATIONS_EXIT_RC=0`, ROS 브리지/RSP `SIGINT_CLEAN`, **SIGKILL 없음**, 전체 종료 `rc=0`.
- 이전 광학 프레임 수정 이후 검수 [#43439967544](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43439967544)와 제어 서비스 시험 [#43440845050](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43440845050)은 RGB/Info/TF는 PASS했지만 Gazebo 종료 교착으로 전체 CI FAIL이었다. 최종 성공으로 실패 기록을 덮어쓰지 않는다.

**결론: Issue #127의 '원본 OGRE2 RGB-D 센서 RGB Image/CameraInfo 미발행 및 Optical TF 미연결'은 `SCOPED_PASS`로 해결.** 기존 OGRE2·원본 카메라를 유지한 실제 데이터 발행 검수 결과다.

## 4. 별도 인수가 필요한 범위

`/camera/depth_image`와 `/camera/points`는 최종 `gz topic -l`에서 존재하는 것으로 확인했으나 **실제 Depth 메시지 픽셀·PointCloud2 파싱, RGB/Depth 정렬·좌표 투영·정확도는 NOT_RUN**이다. ROS 브리지에서 실제 Depth와 Points를 구독해 성공했다고 주장하지 않는다. WSL2 WSLg/RViz GUI, 실제 로봇, Ch07 §7.7 완전한 Pick-and-Place·물리 파지 또한 **NOT_RUN**이다. 전 장 합격으로 승격하지 않는다.

---

## 2026-10-20 과거 STATIC_REVIEW_ONLY 이력 (원문 보존)

# SECTION_7_2_REPORT_KO — Gazebo Harmonic 카메라 센서 설정 및 데이터 수신

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.2절
> 판정: **BLOCKED — 센서 구성과 실행 경로 불충분**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro)
- [Ch07/ros2_ws/src/vision_basics/urdf/two_dof_arm.urdf.xacro](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/urdf/two_dof_arm.urdf.xacro)
- [Ch07/ros2_ws/src/vision_basics/launch/display.launch.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/launch/display.launch.py)
- [Ch07/ros2_ws/src/vision_basics/vision_basics/simple_image_subscriber.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/simple_image_subscriber.py)
- [Ch07/ros2_ws/src/vision_basics/setup.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/setup.py)

## 3. 핵심 발견사항(심각도 기준)
1. **[BLOCKER] my_robot.urdf.xacro에 camera_link/camera_optical_frame 및 활성 camera sensor 정의가 없다.** 원고의 camera.xacro를 연결했다는 실습 경로가 검증되지 않는다. RGB-D(컬러+depth) 센서인지 일반 RGB 카메라인지도 명시·검증해야 한다.
2. **[BLOCKER] 원고의 my_robot_pkg/simulation.launch.py 실행 경로가 Ch07의 확인된 패키지와 다르다.** 확인한 display.launch.py는 two_dof_arm.urdf.xacro를 사용하며 RViz 설정을 별도 my_robot_description 패키지에서 찾는다. Ch07 단독 overlay에 이 의존성을 제공하지 않으면 launch가 실패할 수 있다.
3. **[HIGH] Gazebo 브리지가 존재한다는 보장이 없다.** display.launch.py에는 확인한 범위에서 /camera/image_raw, /camera/camera_info 및 depth 브리지가 없다.
4. **[HIGH] simple_image_subscriber.py는 있지만 setup.py console_scripts에 미등록.** ros2 run vision_basics simple_image_subscriber 경로가 실행되지 않는다.
5. **[MEDIUM] 센서 시스템 플러그인은 SDF world(서버 측)와 카메라 구현을 함께 확인해야 한다.** camera sensor 내부에 시스템 plugin만 삽입했다고 정상 발행을 보장할 수 없다. 광학 프레임의 축과 Gazebo sensor frame_id도 일치해야 한다.

## 4. 수정 권고 및 교육 설계
- 카메라 센서가 있는 Xacro/SDF와 Sensors 시스템 플러그인을 실제 적용 경로로 결선하고 RGB 및 depth 토픽/인코딩 계약을 확정한다.
- URDF camera_link → camera_optical_frame 정적 TF 추가 후 frame_id와 optical 축을 테스트한다.
- 독립 Gazebo launch와 ros_gz_bridge 매핑을 함께 제공하고 Ch07의 실행 명령을 단일화한다.
- setup.py에 simple_image_subscriber console script, package.xml에 sensor_msgs/rclpy/ros_gz_bridge 등 실제 런타임 의존성을 선언한다.
- display.launch.py가 외부 패키지에 의존하면 명시적 선행조건을 제공하거나 Ch07 자체 패키지로 고친다.

## 5. 테스트·Evidence
- **수행:** my_robot.urdf.xacro와 display.launch.py, simple_image_subscriber.py, setup.py 정적 대조.
- **확인:** 카메라 프레임 미포함, 실행 엔트리 미등록, 외부 my_robot_description 참조.
- **미수행:** 실제 Gazebo Harmonic render/bridge/hz/RQt 검증. 원고의 29.851Hz 등은 측정 Evidence로 채택하지 않음.

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_2_GUIDE_KO.md](LAB_7_2_GUIDE_KO.md).
