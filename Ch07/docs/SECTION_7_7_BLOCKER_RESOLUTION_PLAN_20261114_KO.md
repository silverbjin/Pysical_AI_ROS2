# Ch07 §7.7 BLOCKED 해소 — 실측 Pick-and-Place MVP 개발·검수 계획

> **문서 유형:** 실행 전 설계/인수 계약. **본 문서 작성으로 §7.7 기능이 PASS가 된 것이 아니다.**  
> **기준 소스:** `silverbjin/Pysical_AI_ROS2`, 원격 `main@813d29139c28ee5292d60347ce6d96750a11483c` (2026-11-14).  
> **추적:** [Issue #173](https://github.com/silverbjin/Pysical_AI_ROS2/issues/173), 총괄 [Issue #118](https://github.com/silverbjin/Pysical_AI_ROS2/issues/118).  
> **보류:** Ch10 [Issue #123](https://github.com/silverbjin/Pysical_AI_ROS2/issues/123) **HOLD** — 코드 변경·실제 보행 검수 전면 제외.  
> **교육 목표:** 기존 Ch07 로봇 모델과 ROS 2 Jazzy/Gazebo Harmonic에서 단일 물체를 실제 RGB-D로 감지하고, 해당 관측에서 도출한 TCP 목표에 팔을 이동시켜 **동적 물체를 물리적으로 집고 들어 올려 지정 영역에 놓기**.

## 1. 직접 확인한 실제 소스와 결함

| 기능 | 현재 실체 | 판정/수정 경계 |
|---|---|---|
| RGB-D/TF | `vision_basics/urdf/my_robot.ros2_camera_gazebo.xacro`, 실제 RGB-D/CameraInfo/Depth, optical TF, native pointcloud frame 교정 실측 | §7.2 기존 PASS 범위 재사용, **원본 camera Xacro 재개발 금지** |
| 검출 | `vision_basics/object_detector.py`: `/camera/target_pixel` PointStamped, `/camera/target_valid` Bool | §7.4 synthetic 실제 ROS 통신 증거 재사용. `point.z`는 **contour area(px²)**, depth(m)가 아님 |
| 좌표 | `vision_basics/coord_transformer.py`: `/camera/target_3d_base` PointStamped(frame=`base_link`, m), 촬영 시각의 Depth/K/TF 검사 | §7.5 synthetic ROS 검증 증거 재사용; 실제 RGB+Depth 동일 프레임 감지는 통합 테스트에서만 신규 확인 |
| 미션 | `vision_basics/mission_controller.py`는 `target_object` TF를 조회하고 함수 인자 `t_x,t_y,t_z` 대신 상수 `move_arm(1.0,0.0,...)`를 실행 | **BLOCKER**. 실제 `/camera/target_3d_base`를 사용하도록 교정, 카메라 미검출 시 Goal 0건 |
| 엔트리 | `vision_basics/setup.py`에 mission controller console entry 없음 | **BLOCKER**. `ros2 run vision_basics mission_controller` 1개 등록 |
| 그리퍼 | `gripper_controller.py`는 실 GazeboSimSystem의 `/gripper_group_controller/follow_joint_trajectory`, 손가락 두 개 open(0.005m)→close(0.020m), Goal 결과·JointState 확인 | §7.6 실제 **관절 동작까지만** 통과. 새 그리퍼 엔진 제작 금지 |
| 컨트롤러 설정 | `vision_basics/config/ros2_controllers.yaml`은 arm/gripper FJT, 반면 `my_robot_moveit_config/config/moveit_controllers.yaml` gripper는 `GripperCommand`/gripper_cmd | MoveIt은 **arm 그룹** 계획·실행, gripper는 기존 **독립 FJT**를 우선 사용. 한 런타임에서 불일치한 controller type 혼용 금지 |
| 물리 파지 | 손가락만 움직임. 대상 dynamic world pose·접촉·lift·release 실측 없음 | **신규 통합 시험 1개**로 확인해야 §7.7 SCOPED E2E PASS |

**기술적 우선 위험:** (a) RGB-D 카메라, 그리퍼와 arm GazeboSimSystem을 하나의 `robot_description`으로 합쳐야 함. (b) 물체 위치가 카메라 시야 내와 팔의 실제 IK 작업공간 내에 동시에 존재해야 함. (c) 현재 팔은 5개 구동 관절이므로 임의 6DOF 방향의 grasp pose를 강제할 수 없음. (d) 오래된 Bool validity는 Header가 없으며 목표 유실·새 관측 재개 타이밍을 분리해야 함. (e) `mission_controller.py`는 무기한 server wait와 future polling을 포함해 timeout/취소/정상 종료 설계가 필요함. (f) Gazebo 모델의 바닥 지지·가벼운 원통 접촉·손가락 방향/마찰을 검증하지 않으면 Goal 성공이 파지 성공을 의미하지 않음.

## 2. 최소 아키텍처: 데이터를 한 경로로 연결한다

```text
Gazebo OGRE2 original RGB-D + dynamic red object (test-only world)
   /camera/image_raw (Image), /camera/depth/image_raw (32FC1)
   /camera/camera_info (CameraInfo), optical TF at capture stamp
         │
         ▼
object_detector (기존)   pixel (u,v), valid; z=area(px²)
         │
         ▼
coord_transformer (기존)  Depth + K + TF → /camera/target_3d_base
         │
         ▼
mission_controller (수정)
  [유효성/갱신시각/작업공간/단일 목표 잠금]
         ↓
  [물체 surface point → shape center → pre-grasp/grasp/lift/TCP Pose]
         ↓
  [MoveIt /compute_ik + /move_action, first plan_only]
         ├──── arm_group_controller: FollowJointTrajectory (5 joints)
         └──── gripper_group_controller: FollowJointTrajectory (2 joints)
         │
         ▼
Gazebo native pose + contact + actual finger/arm /joint_states
         │
         ▼
독립 witness: REAL_GRASP / LIFT / PLACE / CLEAN_SHUTDOWN verdict
```

MoveIt PlanningScene의 CollisionObject/AttachedCollisionObject는 **경로 계획용 충돌 표현**이다. Gazebo 물체를 움직이는 물리적 고정 조인트나 강제 `set_pose`로 사용하지 않는다. 접근 과정에서 목표 물체와 그리퍼의 정상 접촉만 제한적으로 허용하고 작업대·자체 충돌은 유지한다. 물체에 대한 surface depth와 손끝의 TCP/contact-center offset은 별도 파라미터로 선언한다. **기존 소스에 있는 고정 좌표는 비교용 기록만 남기고 실행 경로에서는 제거한다.**

## 3. 수행 순서: RED→GREEN 및 선행 게이트

| Gate | 작업 | 신규 시험/증거 | 다음 게이트 승인 |
|---|---|---|---|
| **G00 — 소스·월드 일관성** | Ch07에서 기존 robot description+RGB-D Xacro+ros2_control을 통합하는 **최소 test-only wrapper**, 1 Gazebo Sensors·1 control plugin·1 RSP·1 controller owner. MoveIt 5DOF 관절 명칭과 SRDF, action 명칭 대조 | Xacro/URDF 유효성·중복 plugin/static vs dynamic object 가드·실행 configuration diff. 기존 RGB/Depth/그리퍼 시험 재실행 금지 | 구성·클래스·관절 명칭 불일치 0 |
| **G01 — 목표 계약** | mission의 TF polling 대신 `/camera/target_3d_base` 구독, finite `xyz`, `base_link`, 촬영 timestamp, target valid, max age, workspace, 1회 latch, stale/invalid 후 재실행 차단. `setup.py` 등록. async action timeout/cancel/response 코드 판정 | 순수 Python RED→GREEN + 실제 ROS synthetic valid/invalid 토픽. **`plan_only` / `execute` 호출 0**. 2개 다른 목표에서 다른 산출 Grasp Pose 생성, invalid 8종에서 0 Goal | 정상 목표 하나만 `READY_TO_PLAN`, invalid 0 Goal |
| **G02 — 실제 비전·좌표** | 기존 OGRE2·Depth·CameraInfo·TF와 기존 detector/coord_transformer를 하나의 world에 연결. 색상/Depth 같은 픽셀인지 확인하고 dynamic 빨간 원통 하나를 카메라 FOV+팔 작업 공간의 교집합에 배치. 타깃의 표면점→중심·TCP 환산. | 실제 ROS image/depth/header + gz model pose 간 위치 오차. Source/fixture blob SHA, 생성한 `target_3d_base` raw record. **아직 물리 Goal 0** | center 또는 surface offset 보정 후 오차 ≤0.03m 잠정(형상 고정 시 수치 확정), TF/스탬프 유효 |
| **G03 — 계획·팔 실동작** | 기존 MoveIt `arm_group`의 5DOF 현실적인 자세만 사용. `/compute_ik`→`/move_action`에서 첫 실행은 `plan_only=true`, current scene/limits/collision 확인. 그 뒤 **별도 제한적 시뮬레이션 실행 모드**에서 pre-grasp→approach→retreat, 직접 FJT 그리퍼를 순차 호출 | plan_only 중 physical command 0건, IK result, trajectory, action accepted+SUCCEEDED+MoveIt error code SUCCESS, Gazebo 5 arm/2 finger actual JointState, timeout/cancel/clean shutdown | target xyz가 실제 각 단계 계획에 반영·동작, goal/result 일치 |
| **G04 — 물리 grasp/lift/place** | 테스트 전용 single cylinder `static=false`·충돌·질량·마찰 설정과 빈(bin) ROI 1개, 로봇 base 지지 확인. 한 통합 세션에서 pregrasp→descend→close→verify_contact→lift→move→open→settle. 강제 위치 변경/부착 금지 | **독립 Gazebo ground truth** pose, contact pair, object-to-TCP relative pose, finger/arm joint states, rosbag 또는 raw JSON, 명령·시각·source SHA, 원본 종료 코드 | 실제 물체 lift≥0.05m, grasp 유지≥1s, 정상 놓기 후 ROI 안정, contact & release PASS |
| **G05 — 도서·최종 인수** | 실제 RUN/Artifact 독립 검사, `LAB_7_7_GUIDE_KO.md` 명령·예상 로그·터미널 분리/종료 갱신, #118/#173 판정. WSL2 1회 GUI는 별도 Owner 수락 | CI-only real-physics `SCOPED_E2E_PASS`와 WSL2 GUI `MANUAL_REQUIRED/PASS` 구분 | #173은 자동 실측 조건 충족 시 범위 기재 후 종결; 98절 전체 PASS로 승격하지 않음 |

**MVP 범위:** 물체는 단일 색상·형상·목표 1개, 정해진 짧은 pick-and-place 시퀀스 하나, 실제 물리 모델 1개. 좌표 보정·접근 방향·물체 중심 보정은 이 최소 모델로 검수한다. **여러 물체·동적 추적·복잡한 최적 파지·MoveIt Task Constructor·YOLO 재구현·실제 하드웨어는 이번 범위에 넣지 않는다.**

### 필수 실패 시험과 성공 판정

1. **G01:** `target_valid=false`, no target, NaN/Inf, 오래된 stamped point, 잘못된 frame, 범위 외 점, TF 없음/오래됨, IK 실패, action server 없음, duplicate target의 경우 잘못된 새 모션 Goal **0건**. 각각 실패한 입력만 차단하고 실제 성공한 입력을 인위적으로 삭제하지 않는다.
2. **G02:** `target_3d_base`는 `base_link` m, 진짜 깊이 및 촬영 시각으로 계산한 값. 실제 Gazebo world object pose와 비교할 때 광학 surface→형상 중심 교정 포함. **RGB 임의 픽셀 + 독립 Depth를 섞어서 합격시키지 않는다.**
3. **G03:** plan_only 결과는 모션 미실행과 분리해 판정. MoveIt 성공만으로 팔 물리 도착을 증명하지 않으며 실제 GazeboSimSystem의 관절 상태와 MoveGroup/GetPositionIK 반환을 **모두** 확인한다. 그리퍼는 FJT에 대응하도록 독립 호출.
4. **G04:** world Z가 물리적으로 최소 `0.05m` 상승하고 물체가 TCP에 상대 정지 상태로 최소 `1s` 붙어있으며, 실제 손가락–물체 접촉 증거와, 놓은 뒤 목적 ROI 안정 정착이 필요. 해당 숫자는 **개발 전 제안 게이트**로 실측된 성공 수치가 아니다. 단순 로봇팔/그리퍼 Action `SUCCEEDED` 또는 MoveIt AttachedCollisionObject만 존재하는 경우 **물리 파지 FAIL**.
5. **G05:** 최종 exact-tested source SHA, GHCR image digest, 모든 test-only fixture diff, PID/ROS_DOMAIN_ID/GZ_PARTITION, ROS/Gazebo 로그, 원본 Artifact, 취소/종료 상태를 저장. 이전 성공 run의 일부를 새 임무의 물리 PASS로 합산하지 않는다.

## 4. CI·작업 병합/재검 규칙

- 기존 이미지 재사용: `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`, *필요한 런타임 add-on은 버전·해시 별도 기록*. Docker 이미지를 태그만으로 비교하지 않는다.
- 각 Gate는 **별도 좁은 공개 CI**(G00~G01 빠른 static/ROS, G02 OGRE2, G03 MoveIt, G04 물리). 이미 통과한 camera/optical/detector/3D/gripper의 독립 회귀는 성공 증거를 조회만 한다. 조건이 다른 새 통합 시험은 이전 성공과 다른 **새로운 경계**이므로 한 번 실행 가능하다.
- 권장 신규 파일(아직 존재하지 않음): `ci/ch07_77_contract_test.py`, `ci/ch07_77_integration_once.sh`, `ci/ch07_77_ground_truth_witness.py`, `.github/workflows/book-ch07-77-pick-place.yml`. 사용자 원본 테스트 자산은 변경하지 않고 Ch07 test-only wrapper/fixture를 명시적으로 선언.
- 모든 새 PR: **RED 원본 로그 → 최소 수정 GREEN → REFACTOR(변경이득 있으면) → 증거 리뷰 → 병합**. HEAD 소스가 바뀌면 변경 파일이 영향을 준 실패 Gate만 검증. 이미 PASS한 OGRE2 camera / gripper 원샷 전체를 새 PR마다 자동 실행하지 않는다.
- G02가 막히면 카메라 데이터·시야·TF만 분석, G03이 막히면 IK/MoveIt/컨트롤러만 분석, G04가 막히면 **동적 접촉·그립 상대 좌표·마찰/충돌 설정만 분석**한다. 합격 기준을 완화하거나 teleport를 사용해 GREEN을 만들지 않는다.
- G04/ROS 동작은 **시뮬레이션 전용**이며 소유 프로세스 종료, 도메인/partition 격리, bounded wait 및 timeout, 미승인 하드웨어 전달 차단. 첫 시연은 **한 개 냉시작 full-run + 실패 입력 0-Goal 단일 케이스**가 원칙이며, 무조건 3회 반복 검수는 추가하지 않는다.
- **Ch10 #123 HOLD**, Ch09/Ch11 재검수와 Ch13의 다른 통합 플랫폼도 범위 외.

## 5. 이슈/최종 기록 판정 정책

- `PLAN_APPROVED`: Issue #173과 본 설계 문서 존재 — **현재 목표**.
- `CONTRACT_PASS`: G01 synthetic 실제 ROS + invalid Goal 차단.
- `REAL_RGBD_TARGET_PASS`: G02 실제 Gazebo RGB-D target-to-3D point.
- `MOVEIT_GAZEBO_ARM_PASS`: G03 plan_only 및 실제 목표 팔 관절 결과.
- `REAL_PHYSICAL_PICK_PLACE_PASS`: **G04 동일 세션** 실제 세계 좌표·접촉·들기·놓기.
- `CH07_77_SCOPED_E2E_ACCEPTED`: G04 + shutdown + raw artifact/head SHA 원본 독립 감사 완료. 그 전까지 BLOCKED 유지.
- `MANUAL_REQUIRED`: WSL2 GUI 시연/시각 확인. 현장 시연 성공 전에는 GUI PASS 없음.

**종료 기준:** Ch07 §7.7을 도서에서 `SCOPED_E2E_PASS`로 소개할 수 있는 최소 조건은 새 단일 통합 CI 세션에서 원래 RGB-D 인식부터 물리 접촉·월드 pose 기반 목표 영역 release까지 재현된 사실이다. **성능/재현성·실기 안전성·다물체 파지를 포함한 보편적인 시스템 성공 인증으로 승격하지 않는다.** 
