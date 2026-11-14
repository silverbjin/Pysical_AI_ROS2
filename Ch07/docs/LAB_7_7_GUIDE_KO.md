# LAB_7_7_GUIDE_KO — 7.7절 인식 기반 pick-and-place 전체 파이프라인 구축

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> **현재 main 기준 재점검:** 이전 2026-10-20 원본 코드 리뷰 결과를 이력으로 유지하면서 2026-11-14의 기통과 CI·Artifact를 연결함. 원본 7.7의 미션 입력 결손은 아직 해결되지 않음.
> 판정: **BLOCKED — 인식·좌표변환·미션 간 계약 단절 (7.2~7.6의 개별 SCOPED PASS와 별개)**
> 실제 ROS 2/Gazebo/MoveIt 실행 검증: **미수행**. 아래 절차는 수정 후 점검을 위한 실습 가이드이며 실측 성공 증거가 아니다.

## 출판 전 필독 — 무엇이 실제 통과했고 무엇이 아직 실행 불가능한가

| 구성 요소 | 실제 검수 증거 | 정확한 수락 범위 |
|---|---|---|
| 7.2 Gazebo RGB·Depth·CameraInfo·TF | [#43442224511](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43442224511), [#43457034068](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43457034068), [#43473755483](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473755483) | OGRE2 실제 RGB/Depth/Cloud 숫자, PointCloud 좌표축 구별 및 투영 1.06mm 중앙값, **시야 내 시험용 표적만** |
| 7.3 실제 ROS CvBridge | [#43349103331](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43349103331) | Synthetic 이미지의 OpenCV 엣지 처리 |
| 7.4 물체 감지 | [#43350043334](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43350043334) | Synthetic 빨간 물체 중심과 invalid 처리 |
| 7.5 2D→3D 변환 | [#43352872591](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43352872591) | Synthetic Depth/K/TF와 invalid 차단 |
| 7.6 그리퍼 | [실제 동작 #43354355284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354355284)와 [종료 전용 #43358805356](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358805356) | 실제 Gazebo 두 손가락 개폐 및 별도 종료 검증; **실물체 물리 파지 없음** |
| **7.7 전체 미션** | **없음** | **BLOCKED**: 감지→3D 목표→MoveIt→물체 실제 파지/운반/배치 연결 미구현 |

현재 `setup.py`에는 `object_detector`, `coord_transformer`, `gripper_controller` 엔트리만 있고 **`mission_controller` console_script는 등록돼 있지 않습니다**. `mission_controller.py`는 `/camera/target_pixel`이나 유효한 3D 목표를 구독하지 않고 `target_object` TF를 기다립니다. 이어서 미션 함수에 전달된 목표 `(t_x,t_y,t_z)`를 쓰지 않고 `move_arm(1.0,0.0,...)` 등의 **고정 좌표로 명령**합니다.

**따라서 원본 `mission_controller.py`를 실행하거나 임의로 정적 `target_object` TF를 만들어 MoveIt Goal을 승인해도 이를 '인식 기반 집기' 실습 성공으로 간주하지 않습니다.** 교육용 출판 기본 실습은 7.2~7.6의 독립 부분 시연까지입니다. §7.7은 지금 단계에서 후속 종합 프로젝트 과제로 표시하고, 이 가이드의 아래 단계는 **구현·검증 체크리스트이지 합격한 일괄 실행 명령이 아닙니다**.

### §7.7 정식 PASS로 변경하기 전에 필요한 하나의 증거 체인

`target_pixel / target_valid` → 동일 시각 Depth+K+TF를 이용한 `target_position(base_link, m)` → 해당 목표가 실제 pre-grasp/approach/retreat 계획에 사용됨 → 실제 FollowJointTrajectory Goal/Result → **Gazebo 대상 물체의 동적 world pose가 집기·상승·배치까지 이동**. 여기에 invalid depth/stale TF/IK failure에서 **Goal을 보내지 않는 차단**과 종료·회수 로그가 필요합니다. 동일 프로세스에서 모두 확인하기 전에는 성공한 부분을 합산하여 전체 PASS로 승격하지 않습니다.

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

점검해야 할 사실: vision_basics라는 패키지명, mission_controller 엔트리 누락(반면 object_detector 엔트리는 현재 등록됨), target_object TF의 공급자가 누구인지, 하드코딩된 이동 좌표 존재 여부, 실제 ros2_control controller 종류. Ch08~Ch13의 오버레이 설치물을 Ch07과 섞지 않는다.

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
