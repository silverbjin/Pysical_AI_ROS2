# Ch07 §7.7 — 성공 사례를 baseline으로 적용한 동일 물리월드 RGB-D 및 supported release 검증 보고
_2026-11-17 | 3개 작업 계획 중 작업① | 공개 CI 우선 | Draft PR #204_

## 0. 실제 판정

| 부분 | 실제 판정 |
|---|---|
| **G04B 80mm 물리 원통과 로봇 고정 베이스/0.35rad Bin을 동일 Gazebo 월드에서 구성** | 소스와 실제 native pose SCOPED PASS |
| **동일 월드 실제 OGRE2 RGB/Depth/CameraInfo/TF → G01 one-shot** | [공개 CI #43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) **SUCCESS**, **SAME_WORLD_REAL_RGBD_G01=SCOPED_PASS** |
| **실측 front surface→rod center→기존 G04B grasp wrist 오프셋 보정** | 순수 수치 L0 PASS, 실제 5DOF motor Goal 0 |
| **공식 MoveIt의 place→open→retreat 구조를 C17 물리 시작 자세에 적용** | **원래 수직 하강으로는 손목이 Bin에 먼저 충돌 — FAIL/REJECT** |
| 측면 분리 후 지지 배치의 유효한 관절/MoveIt FCL 계획 | **NOT_VERIFIED / STEP1_BLOCKED** |
| G04B native 무충돌 파지·해제, 전체 Ch07 §7.7 E2E | **BLOCKED**, 물리 Goal 0 / Owner WSL2 NOT_READY |

## 1. 공개 성공 사례 — 그대로 복제하지 않고 구조만 채택

- 공식 [MoveIt 2 Task Constructor Pick-and-Place](https://moveit.picknik.ai/main/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html): approach→close→lift→place→open/detach→**별도 retreat**. [MoveIt Task Constructor Place](https://moveit.github.io/moveit_task_constructor/tutorials/pick-and-place.html)의 SimpleUnGrasp와 setRetractMotion이 배치/개방/퇴피 단계를 명시. 우리 5축에는 MTC dependency 새로 도입하지 않고 기존 MoveIt/FJT로 **논리적 순서만 채택**.
- [Sammykrishna/foundationpose-ros2](https://github.com/Sammykrishna/foundationpose-ros2): Jazzy/Harmonic/MoveIt/RGB-D/실제 접촉 기반 6축 robot 성공 시연. 프로젝트 README는 3회 중 1회 전체 성공이라고 한계를 명시한다. **native 접촉과 실제 물체 pose** 검증의 근거만 참고. SAM2/FoundationPose/UR5e 모델은 포팅하지 않는다.
- [EveningStudy/pick-place-robot](https://github.com/EveningStudy/pick-place-robot) 사례는 detachable joint + release 이후 물체 위치 재조정이 있으므로 **물리 인수 baseline에서 제외**.
- 광학 좌표·브리지는 Gazebo Harmonic [ros_gz_bridge 문서](https://gazebosim.org/docs/harmonic/ros2_integration/)의 표준 방식과 기존 Ch07 원본을 유지.
- 선정 기준과 한계: [사전 리서치](CH07_77_STEP1_PHYSICAL_SUCCESS_BASELINE_RESEARCH_20261117_KO.md). 참고 사례의 영상/README가 **우리 원본 로봇·월드의 합격을 대체하지는 않음**.

## 2. 실제 동일 월드 RGB-D 인수 — 성공한 원본

- **source:** 이전 [물리 PR #202](https://github.com/silverbjin/Pysical_AI_ROS2/pull/202)에서 검증한 `ci/ch07_77_g04b_physics_fixture.py`, `ci/ch07_181_bin_yaw_single_factor.py`, `ci/ch07_181_fixed_world_base_anchor.py`를 **source blob 그대로** 필요한 부분만 [통합 PR #204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204)에 선택 재사용.
- **동일 world fixture:** 동적 빨간 원통 radius .012m, **height .080m**, mass .05kg, initial world pose (0.700,0,1.940)m; 6mm 얇은 실제 지지대 top z1.90m; 실제 bin centre (0.55,.25,1.63)m, yaw=.35rad; test-only fixed world→base_link. 가짜 depth/목표/물체 attach/teleport 없음.
- **센서:** 이전 G04A에서 검증된 `object_detector`, `coord_transformer`, `mission_controller`, 원래 `my_robot.pick_gazebo.urdf.xacro` 카메라 및 Gazebo OGRE2/ros_gz_bridge 토픽 재사용. 이전 240mm G04A 원통의 저장된 target을 이번 80mm 물리월드로 복사하거나 주입하지 않았다.
- **결과:** [Run **#43984345894**](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) **SUCCESS**, [Artifact **#14284262397**](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894/artifacts/14284262397), ZIP SHA256 `c50a2add8935fab85e43e0aa271e7622cfd18233352b8938720b3afe24fadbec`. 실제 Actions checkout source SHA **`bf30ced926d7e962d6f272a8316fca90913858aa`** (PR merge commit; PR HEAD와 다름).
- `g04a_live_receipt.json` 원본 **SCOPED_PASS**: RGB/Depth/K **40/40/40**, red pixel target 9, actual `target_3d_base` 2, G01 target_ready **1**, valid Bool positive 9, joint_state 349. 실제 인식 `PointStamped` stamp **16.204s**, frame=`base_link`, XYZ=(**0.6880574608, 0.0011689713, 1.9436128276**)m. `coord.log` 같은 timestamp 16.204와 동일 XYZ; model native `gz_red_pose.txt`=(**0.700000,0,1.940000**)m.
- **표면→중심 실측 차이:** (0.0119425392, −0.0011689713, −0.0036128276)m (동일 고정 `base_link==world` 테스트 월드). 카메라 방향의 X 표면 오차가 **원통 반지름 12mm와 거의 동일**하다. 이 단일 값은 고정 시험 fixture의 보정 근거일 뿐 일반 물체의 robust segmentation/Depth calibration이 아니다.
- 기존 C17의 이 fixture에서의 physical grasp wrist nominal (**.630,0,1.850**)m을 사용한 새 **선택적** `physical_short_rod_profile()` (`mission_geometry.py`): sensor→grasp XYZ=(**.630, .001169, 1.850**)m, pregrasp x=.490, approach x=.560, grasp x=.630. **G04A default source/profile은 변경하지 않았고**, G04B source_id가 지정되지 않은 E2 기본 로직이 short-rod 측정 목표를 임의 승인하지 않도록 fail-closed 유지.
- 센서 시험에서 실제 motor Goal 0, native red cylinder static=false, ROS `GazeboSimSystem`, 정상 종료 `rc=0`, `OWNED_GROUPS_EXITED_NO_SIGKILL`. **MoveIt의 short-rod grasp path FCL/physical 실행은 아직 수행하지 않음**.

### 실패 및 수정 — 같은 원인 반복하지 않음

1. 첫 live [#43983441449](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43983441449) 실패: 검증된 G04B 시험용 DART 패키지가 E2 컨테이너에는 없어서 `dpkg-query`에서 중단. **센서 실패가 아님**.
2. 둘째 live [#43983765332](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43983765332) 실패: 같은 digest의 현재 APT index에서 `libgz-sim8-dev`를 찾지 못해 `apt-get` rc100. 세 번째는 **실제 motor Goal이 없는 센서 확인** 목적에 한하여 DART 1mm 하한 패치를 생략하고 로봇의 **원래 URDF 관절 제한을 유지**, 이 차이를 `dart_profile_scope.txt`에 명시했다. 이는 **실제 물리 모터 인수용 런타임과 완전히 동일하지 않다**.
3. 셋째 [#43984345894](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984345894) 위 동일 물리 world G01 **성공**. 기존 `g04a_live_receipt.json`과 `result.json`은 정상 JSON이다. 부가 `same_world_rgbd_receipt.json`만 마지막에 리터럴 `\\n` 2바이트가 덧붙어 JSON 파서가 종료 오류를 냈다. **원본 내용·실패 경계 보존**. 이후 동일 문자열을 진짜 줄바꿈 `\n`으로 수정하고 L0 정적 테스트 추가, **성공한 실제 카메라 시험을 다시 반복하지 않았다**. 해당 부가 receipt의 실제 CI 당시 machine-readable JSON 계약은 실패이며, 이를 G01 센서 원본 성공과 구분한다.

## 3. 공식 supported-place 구조적 후보 검증 — 부적합 경계 확정

**선정 가설:** 기존 C17 `release + (late) retreat` 또는 C18/C19 `open+simultaneous q3 retract` 대신, **Bin 실제 지지면에서 물체가 지지되는 위치로 먼저 옮긴 뒤 그리퍼를 열고, 손목은 별도 경로로 퇴피**한다. 작업 중 object pose 조작·충돌 삭제·Bin 높이/허용치 완화는 일절 하지 않는다.

실제 [C17 Run #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279) 원본 ZIP `gazebo_rod_finger_contact_same_ecs_frame.csv`, `gazebo_rod_real_static_gravity_velocity.csv`의 native sim time≈69.542s에서 다음을 독립 확인:

| 근거 | 값 |
|---|---:|
| 실제 C17 pre-release 원통 중심 | (0.503606, 0.238149, 1.91499)m |
| 실제 원통 quaternion XYZW | (0.1258657, 0.0265223, 0.1460937, 0.9808726) |
| 회전된 원통의 world 수직 half extent | 0.041738m |
| 원통 하단부터 실제 Bin 윗면 z1.73까지 공간 | **0.143252m** |
| 동일 C17 손목 자세를 유지할 때 Bin 충돌 이전 수직 하강 | **약 0.0658m** |
| 지지면 도달 전의 부족한 간격 | **약 0.07745m** |

- 계산 도구 `ci/ch07_77_step1_supported_release_preflight.py`는 **기존 C17 원본 손목 OBB (0.08×0.06×0.06m)**와 실제 yaw=.35rad 원래 Bin 박스의 **SAT**를 계산, 원통 수직 half extent는 **실제 native quaternion**으로 투영. 0.1mm 보수적 하강 샘플로 최초 wrist–bin 간섭 지점을 탐색한다. 이는 실제 로봇이 하강한 적이 없는 **source-only 구조 가설 검증**이다.
- [L0 #43984578535](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984578535) **SUCCESS**, [Artifact #14283968449](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43984578535/artifacts/14283968449), ZIP SHA256 `00f0b051e3ef1ec857e97e6806a182d04f66299faddc6b11011abf3744c32799`. `supported_place_preflight.json`: **`supported_place_by_C17_vertical_drop_feasible=false`**, `physical_goal_authorized=false`, `status=STEP1_BLOCKED`.
- 따라서 공식 MoveIt Place 순서를 **기존 C17 same orientation에 단순히 수직 하강하도록 구현하면 native 그리퍼가 목표 지지면에 도달하기 전에 wrist–bin 간섭이 발생**한다. 이 후보는 **REJECT**. 이전 C17에서 실제 release 후 wrist–rod native 충돌 648건, C18 620건, C19 535건의 원본 거부 기준도 유지한다.
- **새로운 기하학적 구조 후보:** `SIDE_OFFSET_WRIST_OUTSIDE_BIN_THEN_LOWER_TO_SUPPORT_OPEN_THEN_RETREAT`. 먼저 손목을 Bin 외측으로 분리하면서 **양손 물리 파지 유지**→ 원통만 실제 지지면 바로 위로 이동→ native support contact 확인 후 그리퍼 개방→ 손목 별도 퇴피. 이 구조는 C17 수직/속도 조정과 다르다.
- **현재 검증 결과:** 이 새로운 측면 자세에 대해 **기존 5DOF 제한, 양손 접촉 유지, MoveIt full-body FCL, 같은 dynamic rod collision path**를 모두 만족하는 연결 관절경로를 아직 입증하지 못했다. 그러므로 `CANDIDATE_STATUS=HYPOTHESIS_UNVERIFIED_NOT_EXECUTABLE`; 실제 Goal 송신 0.

## 4. 다음 개발 범위를 확장하지 않는 STOP/GO

```text
G04B_80MM_SAME_WORLD_REAL_RGBD_G01=SCOPED_PASS  # raw 43984345894, NO motor
STEP1_SOURCE_STATIC_UNIT_AND_NATIVE_QUAT_SAT=L0_PASS
STEP1_SUPPORTED_VERTICAL_PLACE=REJECT_C17_BIN_INTERFERENCE
STEP1_SIDE_SUPPORTED_PLACE=HYPOTHESIS_UNVERIFIED
STEP1_READY_FOR_PHYSICAL_L2=NO
G04B_PHYSICAL_CLEAN=BLOCKED
CH07_77_E2E=BLOCKED
STEP2_SIMULATION_MOTOR_E2E=NOT_RUN
STEP3_OWNER_WSL2=NOT_READY
Ch10=HOLD
```

**다음에 꼭 필요한 단일 원인 확인:** 검증된 **G04B short-rod sensor→C17 grasp wrist profile**을 그대로 쓰되, Bin 밖 손목·Bin 위에 지지되는 원통의 **측면 배치 pose/MoveIt FCL path**가 기존 5축/2지 jaw orientation과 실제 양손 grip을 동시에 만족하는지 오프라인 단일 후보로 검증. 그 전에는 실제 motor FJT/유사 물리 L2를 시작하지 않는다. 범용 물체/새 MTC/YOLO/새 구동 시스템·충돌 기준 완화 금지.

## 5. 재사용/출판 기록

- E2 원본 [#43914056590](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43914056590) 센서→MoveIt plan_only SCOPED PASS 그대로. 이번 G04B short-rod sensor는 **새 물리월드에서 필요한 새 경계**이므로 독립 관측.
- 작업①는 **실제 유효 센서 입력·고정 fixture의 표면–중심 캘리브레이션은 충족**, **무충돌 supported-place는 현재 미충족**. 기능 확대보다 이 한 가지 기하학 경계를 해결해야만 이후 Step2 실제 접촉 물리 통합에 착수 가능.
- 참조 [3개 작업 최소 계획](CH07_77_MINIMAL_THREE_WORKSTREAM_EXECUTION_PLAN_20261117_KO.md), [E1/E2 기존 교육 보고서](CH07_77_E1_E2_REAL_RGBD_MOVEIT_DEVELOPMENT_DEBUG_REPORT_20261117_KO.md), [작업① 이전 C17 경계 보고서](CH07_77_STEP1_GEOMETRY_GATE_REPORT_20261117_KO.md).
