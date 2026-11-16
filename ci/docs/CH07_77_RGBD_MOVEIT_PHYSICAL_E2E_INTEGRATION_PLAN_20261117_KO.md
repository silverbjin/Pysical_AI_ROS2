# Ch07 §7.7 실제 RGB-D → MoveIt → 물리 Pick-and-Place 전체 통합 계획
_2026-11-17 | 계획 단계, 구현/인수 미수행 | Issue #173 / #181, 총괄 #118_

> **정의:** 이 작업은 Ch07 §7.7의 end-to-end 기능을 완성하는 통합 개발이다. **개발 완료**와 **실제 단일 세션 물리 인수**를 구분한다. 현재 `CH07_77_E2E=BLOCKED`, `G04B_PHYSICAL_CLEAN=BLOCKED`, `G05=NOT_RUN`, Ch10 HOLD, Owner WSL2 NOT_READY. 본 문서 작성만으로 성공 등급은 바뀌지 않는다.

## 0. 기준 코드와 증거 — 중복 개발 금지

- 원격 `main=9431fb535ce7a51416c19c4395fb2ba3fabdad40` (이 계획 작성 시 확인). **새 통합 브랜치는 main에서 시작**, 과거 물리 Draft #202(HEAD `96d4f4d4b586687b1bc1243cc0e5a9d7901007ef`)는 **진단 증거 소스, 자동 병합 금지**. #202의 base 자체가 main이 아닌 진단 브랜치다.
- **기 검증 센서 체인:** G04A [실제 공개 Gazebo #43552334447](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43552334447): 실제 OGRE2 RGB/Depth/CameraInfo + optical TF + 동적 빨간 24mm rod, `object_detector` → `coord_transformer` → G01 `mission_controller`의 `target_ready`까지 **NO_GOAL scoped success**. `ci/ch07_77_g04a_graspable_rgbd_once.sh`, `ci/ch07_77_g04a_live_small_target_witness.py`, `ci/ch07_77_g04a_graspable_fixture.py`, `my_robot.pick_gazebo.urdf.xacro` 재사용.
- **G01 소스 이미 존재:** `vision_basics/vision_basics/mission_target_gate.py`의 finite xyz / base_link / stamp / recent valid / 2연속 안정 프레임 / one-shot 검사; `mission_controller.py`는 `/camera/target_valid`와 `/camera/target_3d_base`를 구독하여 `/ch07_77/target_ready`, `/ch07_77/pregrasp_candidate` 발행. `setup.py`에 `mission_controller` entry 등록. **단 목표 후보 Pose의 quaternion identity와 Z 오프셋 0은 미교정/미검증**. 이를 IK 검증 없이 실제 Goal로 사용하지 않는다.
- **물리 동작 실험 자산:** #202의 `ci/ch07_77_g04b_actual_physics_witness.py`, `ci/ch07_77_g04b_physical_once.sh`, `ci/ch07_181_rod_trace/`, MoveIt stage/독립 native receipt의 기능을 **필요한 부분만 선택 재사용**. source SHA와 fixture 차이 명시, 1,270행 모놀리식 witness를 그대로 새 mission의 production 로직으로 복제하지 않는다.
- **최대 블로커:** [G04B C01~19 종료 보고](https://github.com/silverbjin/Pysical_AI_ROS2/blob/96d4f4d4b586687b1bc1243cc0e5a9d7901007ef/ci/docs/BOOK_CODE_REVIEW_G04B_FINAL_20261117_KO.md). C17 실제 lift/hold/high/lower/release/ROI 성공해도 native 손목–rod 충돌 **648건**, C18 620건, C19 535건과 최종 XY 0.13708m 실패. **C17은 한계 명시 교육 후보이지 물리 무충돌 PASS 아님**. 현행 #202의 test-only **world-fixed base**, bin yaw **0.35rad**는 원본 구성(yaw 0)과 다르므로 원본 재현 PASS로 바꿔 부르지 않는다.
- **문서 불일치:** 현재 `Ch07/docs/LAB_7_7_GUIDE_KO.md`에는 G01 subscription/console entry가 없다는 옛 서술이 남아 있다. 최종 인수 문서화 단계에서 정정한다.

## 1. 최소 목표 및 기술 아키텍처

**MVP는 한 로봇/한 동적 빨간 원통/한 bin/한 회차/한 명확한 Goal 승인으로 제한**한다. YOLO·다물체 추적·Task Constructor·강화학습·실제 하드웨어·Ch10은 제외한다. Gazebo Harmonic + ROS 2 Jazzy, source/digest/bridge/RMW 구성 고정.

```text
Gazebo OGRE2 real RGB image, aligned Depth, CameraInfo, captured-time optical TF
          │
object_detector.py → /camera/target_pixel [u,v, area(px²)] + /camera/target_valid [Bool]
          │                  `area` is NOT depth; Bool has NO header
coord_transformer.py → /camera/target_3d_base [PointStamped, base_link, metre, image stamp]
          │
existing mission_controller.py + TargetGate → /ch07_77/target_ready [one-shot, NO_GOAL]
          │
NEW bounded mission_executor.py ── phase: observe(default) / plan_only / execute_sim(authorized)
          │   timestamp, frame, source provenance, shape surface→center→TCP calibration
          │   5DOF grasp orientation, FK/IK, collision scene, command provenance
          ├── MoveIt GetPositionIK, MoveGroup plan_only → checked trajectory
          ├── simulated MoveGroup actual arm_group execution (real GazeboSimSystem)
          └── independent gripper FollowJointTrajectory (2 fingers)
          │
native Gazebo dynamic rod poses + same-ECS contact/force + arm/finger JointState
          │
NEW independent E2E witness: RGB source stamp → command Goal → actual lift/hold/release → settled ROI
          │
CI raw Artifact / exact SHA+digest / clean shutdown → ONE owner WSL2 GUI acceptance after CI PASS
```

**제어·데이터 소유권:** 3D 목표는 **센서 토픽에서만** 취득. Gazebo native ground truth는 검증기에서만 사용하고 motion Goal 입력으로 쓰지 않는다. MoveIt이 5축 arm 제어, 그리퍼는 기존 `/gripper_group_controller/follow_joint_trajectory` 직접 FJT 2관절(단일 command owner); `moveit_controllers.yaml`의 기존 gripper GripperCommand/실제 FJT 타입 불일치는 중복 실행을 막고 필요한 최소 adapter/config만 사용한다. PlanningScene CollisionObject/AttachedCollisionObject는 **계획 모델**일 뿐 Gazebo 물체 teleport/attach 명령이 아니다.

**런타임 모드:** `observe`(기본: 모든 Action Goal 0) → `plan_only`(모터 Goal 0) → `execute_sim`(승인된 공개 CI 시뮬레이션만). 시연과 무관한 상시 자동 Goal 실행 금지. Goal 전 IK/충돌/서버/target freshness/시뮬레이션 격리/유효한 runtime owner를 검사. 실패한 경우 새 팔·그리퍼 Goal 0건; 이미 실행 중인 Goal은 bounded cancel/controlled stop 및 소유 프로세스 회수.

## 2. 순차 개발 / 검증 단계

| 단계 | 최소 구현 | 선행 통과/증거 및 다음 진행 |
|---|---|---|
| **E0 baseline 재사용** | main의 G04A 실제 센서/동적 object, G01 gate, 기존 MoveIt/ros2_control, #202 물리 증거를 매핑. world/URDF/SDF·controller/interface·camera optical frame·robot world-base 변환 비교. test-only 원본 차이 Manifest. | 기존 G00~G04A 재시험 **금지**. 실행 대상 조합의 정적 계약 및 SHA만 확인 |
| **E1 센서→임무 Goal 인과 연결** | G01 `target_ready` 구독하는 작은 `mission_executor`, 소스 촬영 stamp·latch ID와 목표 xyz 보존, surface depth에서 원통 중심/파지점/TCP/접근·상승·반출 Pose를 계산하는 별도 순수 Python geometry. `pregrasp_candidate` identity quaternion을 실제 5DOF 목표로 직접 쓰지 않음. | L0: invalid/stale/wrong frame/NaN/no target/duplicate/TF 불가 0 Goal. **서로 다른 실제/주입 목표 A,B의 pregrasp/IK 후보 변화** 수치로 증명. 연결만으로 물리 이동 없음 |
| **E2 실제 RGB-D→MoveIt plan_only** | main G04A의 **동일 camera+로봇+world**에 현존 MoveIt 설정을 최소 연결. 표면→중심 실측 보정, world↔base↔camera↔TCP, collision geometry, 5DOF orientation 및 IK, safe approach/grasp/lift/transport/lower/retreat의 plan_only 검증. | G04A의 같은 stamp RGB/Depth/K/TF에서 나온 3D만 실제 목표. sensor 3D와 native ground truth 대조(가안 3cm 이내; fixture 확정 후 고정). 각 계획의 source xyz 의존성 확인. **모터 Goal 0**. 실패 시 다음 단계 중단 |
| **E3 물리 release 구조 블로커 해결** | C17/18/19 raw에서 해제 직전 rod/wrist world contact geometry, bin 상단, 실제 jaw 열림 경로와 중력 낙하를 오프라인 검토. **손목이 낙하 경로 밖에 놓이는 pre-release pose·release geometry·retreat trajectory를 한 후보로 재설계**. 기존 속도 0.8→0.25 반복 금지. #202 코드 중 최소 기능 재사용, 기존 물리 원본·현재 무충돌 Gate 유지. | 단순 SAT 후보→MoveIt FCL plan_only→필수 제어권 확인 후 **명시적 승인형 L2 1회**. 실제 양쪽 native grip, lift≥0.05m, hold≥1s, high/lower, 실제 release, settled XY≤0.09m/height≤0.055m, **금지된 wrist–rod/wrist–support 충돌 0** 및 종료. 하나라도 실패하면 G04B BLOCKED, E4 physical PASS 금지 |
| **E4 전체 동일 세션 L3** | E2의 센서 Goal을 **E3의 검증된 동적 파지·배치 구동**에 연결. 외부 수동 목표 좌표/fixture world pose를 command 경로에 주입하지 않음. 독립 witness가 이미지 stamp→pixel→3D→target_ready→plan/Goal→JTC reference/feedback→native contact/rod pose→ROI를 동일 source SHA/세션으로 연결. | 실제 한 cold-start 단일 미션 + 별도 invalid input 0-Goal 확인. L3 **SCOPED_E2E_PASS는 E3 clean physical과 sensor-dependent Goal이 동일 세션에서 모두 참일 때만** 선언 |
| **E5 문서·출판·Owner** | `LAB_7_7_GUIDE_KO.md` 이전 G01 오류 정정. 단일 CI/WSL2 공통 실행 entry, 강사 GUI 터미널/모니터 분리/정상 종료·로그, 원본 zip SHA256/이미지 digest/fixture Manifest. 마지막에 Owner WSL2 GUI **1회**. | CI E4 SUCCESS 후에만 수동 WSL2. CI scoped E2E와 Owner acceptance 별도 명시. #173/#118 업데이트, Ch10 HOLD |

**작업이 막힐 때의 규칙:** E2 plan_only까지는 E3 미완료와 독립적으로 구현·검증 가능. E3가 다시 실패한다면 센서·MoveIt 코드를 재시험하지 않고 E3만 BLOCKED. **E3 물리 clean이 통과되지 않는 한 E4/L3·E5/Owner를 PASS로 승격하지 않음**. 에러 원본/시각/변경 요인 없는 반복 L2 없음. 물리 충돌 기준 완화·실물체 teleport/kinematic attach 금지.

## 3. 인수 항목: 기능·안전·원본 증거

1. **실제 센서:** `/camera/image_raw`, `/camera/depth/image_raw`, `/camera/camera_info`, TF의 optical frame·동일 stamp. `/camera/target_pixel.point.z`는 area(px²), 진짜 depth는 Depth image에서 계산. 검출 대상은 동적 테스트용 원통 1개. 실측 정합 오차 목표는 fixture 고정 후 동결(초안 ≤0.03m).
2. **입력 0-Goal:** detector invalid, depth NaN/0, stale/future, TF 실패, frame mismatch, 불가능한 IK, collision plan fail, unavailable Action, 중복/무타깃에서 **신규 모터 Goal 0**, 실패 원인과 timeout/cancel/teardown을 기록. header 없는 validity Bool을 frame동기화 증명으로 쓰지 않음.
3. **계획 인과:** 실제 `target_ready` XYZ/stamp가 pregrasp/grasp/retreat/placement 계산과 MoveIt request에 사용됨을 같은 receipt로 증명. 서로 다른 유효 XYZ에서 다른 요청이 산출되고 고정 Goal 경로가 없음을 L0에서 확인. `plan_only`는 물리 동작 0.
4. **실제 구동:** MoveIt과 arm/2-finger FJT의 Goal UUID/accept/result, 원래 5축/2축 reference·feedback·error/native joints. `SUCCEEDED`만으로 actual pass 처리 금지.
5. **실제 파지/배치:** 원통 질량·gravity·static=false, **Gazebo native world pose** 실제 상승≥5cm, 1s 이상 실제 두 손가락 grip+hold, 운반/해제 후 XY≤9cm, 높이 오차≤5.5cm, 금지 wrist-rod·wrist-support 충돌 **0건**, 불변 raw receipt.
6. **반증:** target A/B를 바꾸면 실제 motion planning target이 바뀌어야 함. 카메라 영상을 가리거나 잘못된 depth/TF를 주면 신규 실제 Goal 0건. 물체의 ground truth를 Goal 산출에 입력하거나 이전 픽셀에 무관하게 같은 hardcoded 위치로 움직이면 E2/E4 FAIL.
7. **프로비넌스:** 실제 source SHA/PR HEAD, pinned runtime `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`(현재 확인된 기존 digest; 준비 이미지 아직 후보), world/robot fixture sha/변경 diff, ROS_DOMAIN_ID/GZ_PARTITION, PID ownership, 최초 FAIL, raw zip/sha256 및 정상 종료.

## 4. CI 운영과 산출물

- **L0 자동**: 변경 파일 관련 Python geometry/mission state/collision/checksum/CLI; 기존 G01/G04A 광범위 반복 금지. 코드+집중 테스트+사이클 보고서는 가급적 **한 커밋**으로.
- **L1 조건부**: 신규 mission_executor 토픽/MoveGroup/FJT Action 연결 계약만 실제 ROS 관측, 여전히 모터 Goal 0.
- **L2 승인형**: E3 첫 실패·오프라인 가설·정적 collision-free 후보·동일 SHA/digest를 문서화한 후 단 1회 Gazebo. CI 전용 소유권, 승인 이벤트 없으면 `SKIPPED`를 올바르게 표시.
- **L3 승인형 단일 E2E**: E3 실제 무충돌 근거 확인 후 한 센서 기반 physical full session. G04A·G04B 과거 서로 다른 Run을 합산하여 L3 PASS 만들지 않음.
- **Owner 최종 인수**: 동일 실행기·이미지 digest/코드 SHA로 WSL2 GUI 1회만. 이전 G04B 디버그 시험을 Owner가 반복하지 않음.
- 기존 `ci/ch07_77_g04a_graspable_rgbd_once.sh`는 baseline, 새 `ci/ch07_77_e2e_once.sh`(예정)는 통합 orchestration. `ci/ch07_77_e2e_witness.py`(예정)는 별도 **read-only** 독립 증거 작성. `.github/workflows/book-ch07-77-e2e.yml`(예정)은 L0와 승인형 L2/L3를 분리. 강사·학생 실행 가이드와 Evidence Ledger/단계별 개발보고서 필수.
- 계획 외 작업: Ch10, 다른 챕터 전면 재검, 새 카메라/YOLO, simulation-to-real, 15회 통계 시험, 목표 수치 완화, 외부 하드웨어, 새로운 범용 로봇 프레임워크.

## 5. 최종 Done 정의 및 중단 조건

- `E2_SENSOR_TO_PLAN_PASS`: 새로운 실제 RGB-D stamp→검출→3D→G01 gate→validated MoveIt plan_only, invalid 0 Action Goal. **이는 전체 완료 아님**.
- `E3_G04B_PHYSICAL_CLEAN_PASS`: 실제 동적 grip/lift/hold/release/ROI 및 원래 금지 접촉 0. **현재 BLOCKED**.
- `CH07_77_SCOPED_E2E_PASS`: **동일 session/source**에서 E2 + E3 모두 실제 execute 통과, 독립 native provenance·clean teardown 확인. **현재 BLOCKED**.
- `OWNER_WSL2_ACCEPTED`: CI 성공 후 동일 명령으로 실제 GUI 1회 현장 인수. **현재 NOT_READY**.

**승인/출고 분리:** 이 계획은 통합 기능의 개발 설계만 고정한다. 실제 Gazebo 모터 Goal 승인 이벤트, 인수 기준 변경, main 병합, Owner WSL2 실행은 이 문서 작성으로 자동 승인되지 않는다. 과거 #202의 물리 실패를 숨기거나 무인 실로봇 안정성을 주장하지 않는다.
