# LAB_7_7_GUIDE_KO — 7.7절 인식 기반 pick-and-place 전체 파이프라인 구축

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20)
> 판정: **BLOCKED — 인식·좌표변환·미션 간 계약 단절**
> 실제 ROS 2/Gazebo/MoveIt 실행 검증: **미수행**. 아래 절차는 수정 후 점검을 위한 실습 가이드이며 실측 성공 증거가 아니다.

## 1. 목표와 선행 조건
이 절은 검출된 객체의 3D 위치를 로봇 TCP의 grasp pose로 변환하고, 계획→접근→파지→확인→이동→배치를 반복 가능한 상태 머신으로 구현하는 종합 프로젝트다.

**원본 코드를 바로 자동 실행하지 않는다.** 현재 object_detector.py는 /camera/target_pixel에 PointStamped를 발행한다. 그러나 mission_controller.py는 이를 구독하지 않고 base_link→target_object TF를 기다린다. 또한 미션 내 실제 이동 목표는 검출된 t_x/t_y/t_z가 아닌 상수다. 이는 end-to-end 시각 기반 그리핑을 검증한 구현이 아니다.

## 2. 환경 및 정적 진단
~~~bash
source /opt/ros/jazzy/setup.bash
cd Pysical_AI_ROS2/Ch07/ros2_ws
printenv AMENT_PREFIX_PATH | tr ':' '\n' | head -20
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash

ros2 pkg prefix vision_basics
grep -n 'target_object\|target_position\|move_arm(' src/vision_basics/vision_basics/mission_controller.py
grep -n 'target_pixel\|PointStamped' src/vision_basics/vision_basics/object_detector.py
grep -A15 console_scripts src/vision_basics/setup.py
~~~

점검해야 할 사실: vision_basics라는 패키지명, mission_controller와 object_detector console entry 누락, target_object TF의 공급자가 누구인지, 하드코딩된 이동 좌표 존재 여부, 실제 ros2_control controller 종류. Ch08~Ch13의 오버레이 설치물을 Ch07과 섞지 않는다.

## 3. 수정 및 단계별 실습 순서
1. **카메라 입출력(7.2):** RGB·깊이·CameraInfo 브리지, TF optical frame, encoding·주파수를 확인한다.
2. **이미지 인식(7.4):** detector PointStamped의 header.stamp·frame_id와 point.x/y 픽셀, point.z 면적(px²)의 계약을 명확히 하고 invalid/stale를 거부한다.
3. **3D 변환(7.5):** 정렬된 depth와 K로 역투영하고 이미지 촬영 시각 TF로 base_link의 PointStamped(m)를 만든다. depth가 없으면 임의 0.5m로 동작을 강행하지 않는다.
4. **계획:** target의 xyz가 실제 pre-grasp/grasp/retreat에 사용되도록 하드코딩을 제거한다. object surface point와 TCP grasp offset 및 자세를 구분한다. MoveIt 2는 우선 plan_only=true로 IK/충돌 제약을 점검한다.
5. **액션:** MoveGroup과 gripper FollowJointTrajectory의 server, goal accepted, 결과 코드와 timeout/cancel을 단계별 기록한다. 그리퍼는 joint_finger1·joint_finger2 두 prismatic joint를 제어한다.
6. **상태 머신:** IDLE→DETECT→PLAN→APPROACH→GRASP→VERIFY_GRASP→LIFT→PLACE→VERIFY_PLACE→DONE 또는 RECOVERY. 이전 타깃 TF가 남아 있다고 자동 재실행하지 않도록 목표 ID, last_seen, 1회 트리거를 추가한다.
7. **실제 물리 확인:** Gazebo에서 물체가 손가락 사이에 들어왔고 리프트에 함께 이동하며 배치지에 떨어지는지 월드 pose로 확인한다.

## 4. 개별 통신 선행 점검
실제 시뮬레이터와 서버를 실행한 상태에서 확인한다. 실패하면 미션 실행 대신 먼저 해당 단계를 복구한다.

~~~bash
ros2 topic list -t | grep -E 'camera|robot/target|joint_states'
ros2 topic info -v /camera/target_pixel
ros2 topic echo --once /camera/camera_info
ros2 action list -t | grep -E 'move_action|gripper'
ros2 service list -t | grep compute_ik
ros2 run tf2_ros tf2_echo base_link camera_optical_frame
ros2 run tf2_ros tf2_echo base_link target_object
ros2 control list_controllers
ros2 pkg executables vision_basics
~~~

TF가 없는 경우 무작정 static transform으로 target_object를 만들어 움직이지 않는다. 가짜 정적 TF를 사용할 경우에는 **좌표 변환·시뮬레이션 plan_only용 fixture**로만 격리하고 실제 영상 탐지 기반 pick-and-place의 성공으로 제출하지 않는다.

## 5. 정상/실패 시나리오 및 수용 기준
| 시나리오 | 확인 항목 | 합격 기준 |
|---|---|---|
| 정상 1개 타깃 | 영상→픽셀→3D→MoveIt→그리퍼 | 전 단계 stamp/frame·액션 성공·물체 pose 이동 |
| 물체 없음 | detector invalid/stale | 고정 위치로 팔이 움직이지 않음 |
| depth 0/NaN/Inf | 3D 좌표 생성 | 목표 publish·동작 차단 |
| TF 누락·지연 | 시각 동기화 | 오래된 TF 사용 차단, 실패 로그 남김 |
| IK 실패·충돌 | 계획 검증 | 충돌 우회 강제 실행 금지 |
| 파지 실패 | 물체 이동 여부 | 성공 처리 금지, RECOVERY 진입 |
| 반복 메시지 | 1회성 수행 | 동일 target 재실행 없음 |

### 제출할 Evidence
- Git commit SHA, ROS 2 Jazzy/Gazebo/MoveIt 버전, colcon build exit code.
- RGB/depth/target 토픽 타입·stamp·frame, TF 지연, action Goal·Result·Status 로그.
- 접근·파지·리프트·배치 장면과 물체 월드 좌표 CSV/스크린샷.
- 실패 실험과 복구 로그(개별 실패 원인별). 단순 **plan accepted**나 그리퍼 action 반환만으로 물체 파지를 성공 판정하지 않는다.

**완료 기준:** 7.2~7.6 전 단계가 검증되고, 특정 물체 ID를 실제 집어 배치지로 이동한 사실과 재현 가능성이 입증될 때만 PASS로 변경한다. 원본 Ch07 상태에서는 BLOCKED이다.

관련 리뷰: [SECTION_7_7_REPORT_KO.md](SECTION_7_7_REPORT_KO.md).
