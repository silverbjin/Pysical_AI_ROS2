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
