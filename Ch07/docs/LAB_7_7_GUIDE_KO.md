# LAB_7_7_GUIDE_KO — 7.7절 인식 기반 pick-and-place 전체 파이프라인 구축

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> **2026-11-17 검증 범위 정정:** 아래 2026-10월의 'G01 엔트리/구독 부재' 결함은 이미 수정됐다. 원격 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40`의 G01은 독립 실행된다. E2 개발·인수 결과는 아직 미병합된 [Draft PR #204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204)에만 있다.
> **실제 성공:** 같은 Gazebo 세션의 RGB-D→G01→MoveIt `plan_only` [#43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) **SCOPED PASS**. 실제 G04B 80mm 물리 test world의 RGB-D/G01 [#43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) **SCOPED PASS**. 모두 arm/gripper 실제 motor Goal 0.
> **미통과:** `G04B_PHYSICAL_CLEAN=BLOCKED`, `CH07_77_PHYSICAL_PICK_AND_PLACE_E2E=BLOCKED`, Owner WSL2 NOT_READY, Ch10 HOLD. CI 계획 성공은 실제 잡기·배치 성공이 아니다.

## 출판 전 필독 — 무엇이 실제 통과했고 무엇이 아직 실행 불가능한가

| 구성 요소 | 실제 검수 증거 | 정확한 수락 범위 |
|---|---|---|
| 7.2 Gazebo RGB·Depth·CameraInfo·TF | [#43442224511](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43442224511), [#43457034068](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43457034068), [#43473755483](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43473755483) | OGRE2 실제 RGB/Depth/Cloud 숫자, PointCloud 좌표축 구별 및 투영 1.06mm 중앙값, **시야 내 시험용 표적만** |
| 7.3 실제 ROS CvBridge | [#43349103331](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43349103331) | Synthetic 이미지의 OpenCV 엣지 처리 |
| 7.4 물체 감지 | [#43350043334](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43350043334) | Synthetic 빨간 물체 중심과 invalid 처리 |
| 7.5 2D→3D 변환 | [#43352872591](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43352872591) | Synthetic Depth/K/TF와 invalid 차단 |
| 7.6 그리퍼 | [실제 동작 #43354355284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354355284)와 [종료 전용 #43358805356](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358805356) | 실제 Gazebo 두 손가락 개폐 및 별도 종료 검증; **실물체 물리 파지 없음** |
| **7.7 E2 계획 전용** | [RGB-D→MoveIt 실제 #43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) | **SCOPED PASS**: 실제 G01 목표로 3개 MoveGroup `plan_only`, 모터 Goal 0. 아직 PR #204 미병합 |
| **7.7 동일 G04B 80mm 물리 월드 센서** | [실제 카메라 #43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) | **SCOPED PASS**: optical RGB/Depth/K/TF → one-shot G01. 물리 파지는 별도 |
| **7.7 전체 실제 물리 Pick-and-Place** | [C17 #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279) 및 후속 C18/C19 | **BLOCKED**: native 손목↔원통 금지 충돌 648/620/535건, 엄격 물리 인수 실패 |

**현재 실제 소스:** `setup.py`에는 `mission_controller`와 `mission_plan_only` 실행기가 모두 존재한다. `mission_controller.py`는 `/camera/target_valid` 및 `/camera/target_3d_base`를 구독해 timestamp/frame/freshness 조건을 만족한 목표만 `/ch07_77/target_ready`로 **1회 승인**한다. 이후 신규 `mission_plan_only.py`는 원래 5축/MoveIt `plan_only`를 호출하며 실제 구동은 명시적으로 금지한다. 이 둘의 성공을 더해도 물리 집기·배치 성공이 되지는 않는다.

**현재 출판 가능한 학습 범위**는 실제 센서→정합된 좌표→미션 입력→MoveIt **계획 전용** 및 실패 사례 해설까지다. C17~C19는 native 접촉·상승·일부 배치 관측에도 금지 손목 충돌이 존재했고, 새로운 overhead 단일 파지 후보도 [원본 기구학·충돌 사전검사](../../ci/docs/CH07_77_STEP1_SINGLE_OVERHEAD_MVP_DISPOSITION_20261117_KO.md)에서 거부됐다. 이 경계를 숨기고 전체 E2E 완료로 선언하지 않는다.

### §7.7 정식 PASS로 변경하기 전에 필요한 하나의 증거 체인

`target_pixel / target_valid` → 동일 시각 Depth+K+TF를 이용한 `target_position(base_link, m)` → 해당 목표가 실제 pre-grasp/approach/retreat 계획에 사용됨 → 실제 FollowJointTrajectory Goal/Result → **Gazebo 대상 물체의 동적 world pose가 집기·상승·배치까지 이동**. 여기에 invalid depth/stale TF/IK failure에서 **Goal을 보내지 않는 차단**과 종료·회수 로그가 필요합니다. 동일 프로세스에서 모두 확인하기 전에는 성공한 부분을 합산하여 전체 PASS로 승격하지 않습니다.

## 1. 목표와 선행 조건
이 절의 **실습 가능 부분**은 실제 RGB-D로 검출한 객체의 3D 표면 위치를 `base_link`로 변환하고 G01에서 승인해 MoveIt **계획만** 검증하는 과정이다. 예전 `target_object` TF polling·하드코딩 arm Goal 문제는 G01에서 해소되었지만, 물리 파지·배치의 동일 세션 성공은 아직 확보하지 못했다. 향후 확장 상태머신은 현재 실습의 구현 완료 항목이 아니라 **검증 체크리스트**다.

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

점검해야 할 사실: `vision_basics` 패키지와 `mission_controller` / `mission_plan_only` **등록 확인**, `target_valid`·`target_3d_base`의 프레임·stamp·G01 one-shot 승인, `planning_options.plan_only=true` 및 motor Goal 0, `GazeboSimSystem` controller 종류. 과거 `target_object` TF 방식은 **원본 결함의 역사적 비교 대상**이며 더 이상 현재 G01 의존조건이 아니다. Ch08~Ch13의 오버레이 설치물을 Ch07과 섞지 않는다.

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
ros2 topic echo --once /ch07_77/target_ready
ros2 control list_controllers
ros2 pkg executables vision_basics
~~~

TF가 없는 경우 무작정 static transform으로 `target_object`를 만들어 움직이지 않는다. 목표는 실제 optical RGB-D 및 촬영 시각 TF→`base_link`로 검증한다. **관찰용 plan_only 실습만 허용**, E3 물리 구동은 미승인이다.

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

**완료 기준:** 7.2~7.6의 검증된 하위 실습과 7.7 E2 plan_only를 **각각 증거 범위로 인정**한다. 물리 Pick-and-Place 전체 PASS는 특정 실제 원통을 집어 목적지까지 이동하고 **native 금지 충돌 0건**을 독립 원본으로 입증했을 때만 가능하다. 현재 전체 물리 인수는 BLOCKED다.

관련 리뷰: [SECTION_7_7_REPORT_KO.md](SECTION_7_7_REPORT_KO.md).

**BLOCKED 해소를 위한 단계별 개발·검수 계획:** [SECTION_7_7_BLOCKER_RESOLUTION_PLAN_20261114_KO.md](SECTION_7_7_BLOCKER_RESOLUTION_PLAN_20261114_KO.md) / [Issue #173](https://github.com/silverbjin/Pysical_AI_ROS2/issues/173). 이 계획은 구현/성공 증거가 아니며, §7.7은 실제 원본 물리 통합 인수가 끝날 때까지 BLOCKED다.


## 6. 출판용 범위 확정 — 단일 overhead 파지 후보 실패 (2026-11-17)

신규 수직 하향 tool·수평 jaw 파지 후보 **하나**만 [보고서](../../ci/docs/CH07_77_STEP1_SINGLE_OVERHEAD_MVP_DISPOSITION_20261117_KO.md)로 검증했다. 픽업 시 원래 1.5m 팔 도달거리보다 약 10.11cm 부족, 배치 시 손목 요구각 2.4513rad로 원래 상한 1.5708rad 초과, 가상 자세의 원래 `link4`-Bin OBB 충돌 분리 실패. [집중 L0](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43993232265)는 **5/5 테스트 PASS**이나 정식 MoveIt FCL·실제 모터·물리 인수가 아니다. **불가능한 Goal을 전송하지 않고 차단한 성공**이다.

- **실습 성공 범위:** 7.2~7.6의 개별 항목, E2 실제 RGB-D→G01→MoveIt 계획 전용, G04B 80mm 동일 물리 fixture 실제 RGB-D→G01.
- **교육용 실패 사례:** C17/C18/C19 native 손목 충돌, C17 수직·측면 지지 배치 기하학 거부, overhead 자세의 도달거리·관절·Bin 충돌 거부.
- **수행하지 않음:** 새 범용 grasp planner/MTC·모터 Goal·Owner WSL2 GUI 물리 인수·Ch10. `main`에 물리 집기 성공으로 병합하거나 홍보하지 않는다.
