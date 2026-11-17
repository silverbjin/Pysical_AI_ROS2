# Ch07 §7.7 — 성공 사례 우선 조사 및 물리 통합 최소 기준선 (2026-11-17)

## 연구 질문

- 기존 E2의 RGB-D→MoveIt `plan_only` 증거를 **실제 파지 가능한 80mm 원통·동일 Gazebo/TF 월드**로 옮겨도 image/depth/K/TF가 유효한 목표를 만드는가?
- 기존 G04B C17/C18/C19의 release-first 또는 open+concurrent-retract 방식은 손목–원통 접촉 648/620/535건을 기록했다. 실물 지지대에 하중을 안전하게 넘기는 **supported placement → gripper open → separate retreat**가 무충돌 상태를 만들 수 있는가?

## 적용 우선순위로 선정한 성공 사례

| 사례 | 검증 가능한 주장 | **이번 프로젝트에서의 재사용** |
|---|---|---|
| [MoveIt 공식 MoveIt Task Constructor Pick-and-Place](https://moveit.picknik.ai/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html) | approach/close/lift/place/open/detach/retreat를 계획 스테이지로 나눈 **공식 구현 가이드**. Place 시 gripper open와 retreat가 구분된다 | **동작 순서 baseline만** 재사용. MTC 패키지 신규 도입 금지. 계획 장면의 `attachObject/detachObject`는 Gazebo physics attachment/teleport 근거가 아님 |
| [MoveIt Task Constructor Place API](https://moveit.github.io/moveit_task_constructor/tutorials/pick-and-place.html) | `GeneratePlacePose`, `SimpleUnGrasp`, `setRetractMotion`를 독립 처리 | 지원면까지 접근해 지지된 뒤 개방, 이후 별도 move-away 경로를 검토하는 구조. ROS 2 Action/FJT 소유권은 기존 그대로 |
| [Sammykrishna/foundationpose-ros2](https://github.com/Sammykrishna/foundationpose-ros2) | 사용자 공개 README: Ubuntu24.04 / ROS2 Jazzy / Harmonic / MoveIt2 / RGB-D + *real contact* gripper. 한 완료 시연은 있지만 3번 시도 중 1번만 전체 성공했다고 밝힘 | 동적 객체 실제 native 접촉·pose와 카메라 재검증의 **개념 참고**. SAM2/FoundationPose, 6DOF UR5e와 고가 GPU 스택 **포팅 금지** |
| [EveningStudy/pick-place-robot](https://github.com/EveningStudy/pick-place-robot) | RGB-D + MoveIt + Gazebo 예제, README에 object detachable joint 및 release 이후 object reposition 지원 명시 | **물리적 진짜 grasp 인수 baseline에서 제외**: detached joint/pose 재배치는 우리 native contact/zero-teleport 계약과 다름 |
| [Gazebo Harmonic ros_gz_bridge](https://gazebosim.org/docs/harmonic/ros2_integration/), [ros_gz example](https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_bridge/README.md) | 실제 Gazebo OGRE2 depth/image/camera_info 토픽을 ROS Image/CameraInfo와 시각·optical frame으로 bridge | 기존 `object_detector`/`coord_transformer`/`mission_controller` 코드와 브리지만 재사용. 새 카메라 드라이버/YOLO 불필요 |

## 선택한 실제 적용 범위 (교재 MVP)

**Baseline A — physical same-world real RGB-D admission (ROS motor Goal 0):**
- 기존 [PR #202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202)의 **가장 최근 G04B 물리 test-only fixture 그대로** 이용: radius .012m, height **.08m**, 50g, real thin support top z1.90, rod world (0.70,0,1.94), 0.35rad solid bin, world-fixed robot base z0 + DART margin 조건. 기존 [PR #204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204)의 **동일 로봇 실제 RGB-D / OGRE2 / CameraInfo / optical TF / G01** 구동. 240mm 원통 E2 관측값은 command source로 재사용하지 않는다.
- 원본 ROS image/depth/info, pixel stamp/area, `base_link` target stamp/XYZ, independent native rod model pose, precise fixture/source SHA를 저장. 80mm 원통의 실제 픽셀 면적이 500px² 임계치를 넘는지는 **미확인**이므로 실물 영상 실패 시 그 원인만 계측, 임계치 임의 완화 금지.
- 충분한 두 연속 유효 target이 실측되기 전에는 `SAME_WORLD_G01_VALID_TARGET=PASS`가 아니다. E2 구동 허용은 전혀 없음.

**Baseline B — placement supported, then release, then retreat (NO motor Goal until FCL):**
- C17 원본의 pre-release arm q=(.509164,-.331197,1.049568,1.569168,-.346061)와 native rod centre (.503606,.238149,1.91499)에서 지금까지 **낙하 경로가 손목 부피와 교차**했다. C18/19의 `open + simultaneous wrist retreat`는 실제 wrist 가 움직이기 전에 (~100ms) rod 가 손목에 부딪혔다. 속도 조절 반복 금지.
- 새 기하학적 원인 가설: **손목이 비워진 supported place 위치에 물체의 하중을 옮기기 전에는 gripper를 열지 않는다.** 용기 받침의 원래 충돌면은 유지하며 별도의 가짜 rod attachment/pose 고정·외부힘·contact 삭제·수용 오차 완화는 금지.
- 물리 전단계 판정: 현재 5DOF/2finger 원래 충돌형상으로 **rod bottom-to-bin support ≤ 1cm**, wrist vs real solid bin clearance ≥3mm, wrist vs rod-drop swept conservative SAT separation >=8mm, jaw 양손 contact/grasp direction, arm FCL plan-only, 실제 scene source/frame을 *동시에* 충족하는 상태가 존재해야 후보 승인. 이 값들은 **후보 선별용 제약**, 전후 native 실제 무충돌 판정은 반드시 0건 유지.
- 충족 불가면 무리하게 실행하지 않는다: `SUPPORTED_RELEASE_CANDIDATE=BLOCKED`, 물리 Goal 0, Step2 NOT_RUN. **다른 전략을 무한 탐색하지 않음**.

## 범위 외

MTC 새 종속성, grasp planner, 새 world generator, ROS services/new Robot API, camera model 변경, 실제 기계, 이미지 ML 학습, 새로운 GPU 이미지, image/depth 가짜 replay, Gazebo object set_pose/teleport/attach, bin/world collision shape 재정의 또는 충돌 threshold 완화, 기존 G00~G04A·E2 독립 PASS 재검증.

## 인수/관찰 방침

성공 사례의 **해결 구조**를 이 프로젝트에서 실제 동일 로봇/물체에서 재현하기 전에는 `CH07_77_E2E=BLOCKED` 유지. CI L0는 물리 인수 대신할 수 없다. 작업 ①에 필요한 **동일 물리 world RGB-D 유효성 확인**과 **하중 지지 후 분리 후보의 기하/FCL 사전 검사**만 진행한 뒤, 실제 안전한 후보가 나오면 신규 물리 L2 1회를 승인형으로 진행.
