# Ch07 §7.7 — Issue #181 finger2 실제 명령 전달·물리 구동 단일 계측

> **결론(2026-11-14 KST): G04B 실제 파지 BLOCKED / G05 NOT_RUN / Ch10 #123 HOLD.** ROS 2 Jazzy + Gazebo Harmonic, 원본 `GazeboSimSystem`, 실제 하드웨어가 아닌 공개 CI 시뮬레이션. 본 문서의 PASS는 **계측·제어 명령 전달에 한정**하며, 도서 §7.7 Pick-and-Place의 물리적 성공 판정이 아니다.

## 1. 단일 계측 목적 및 변경 금지

기존 원본 [CI #43587221825](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587221825)는 **같은 최종 팔 위치, 물체 없는 Gazebo, 직접 arm FJT**에서 finger2 11mm 명령 → 실제 10.986mm로 PASS였다. 그러나 [CI #43587538228](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43587538228)은 같은 월드·관절 목표지만 **실제 MoveGroup 경로 실행** 후 finger2 목표 11mm → 실제 0mm로 ABORTED(-5)였다.

이번에 성공·실패 기인수 시험을 다시 실행하지 않고, **기존에 실패한 단일 환경·단일 finger2 FJT Goal**에만 **읽기 전용** 계측을 추가했다.

- 읽기 ①: `/gripper_group_controller/controller_state`의 Jazzy `reference/feedback/error` 전체 시계열.
- 읽기 ②: **`/controller_manager/introspection_data/full`** 의 `pal_statistics_msgs/msg/Statistics`: 실제 `command_interface.joint_finger2/position`, `state_interface.joint_finger2/{position,velocity,effort}`, `is_limited`.
- 읽기 ③: 독립 ROS `/joint_states`.
- 읽기 ④: Gazebo native `gz model --model my_robot --joint joint_finger2`의 원래 prismatic 축 및 `finger2`/손목 링크 위치의 전후 차이.
- `main` 기존 인수본, 원본 URDF·SDF·로봇 모델, joint axis, controller, goal tolerance, 물리 속성, MoveGroup 경로 **변경 없음**. Force attach/teleport/FakeSystem 없음.

## 2. 재현 결과 — 진단 원본

실제 공개 CI: [#43591347996](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43591347996). 원본 [Artifact #14112930455](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43591347996/artifacts/14112930455) ZIP SHA256: `4dce56e710d900d4ce2d89edbc8a99fda664f02f62e7bc15fc1fb4b8081eed0e`.

실행 코드 커밋: `f4cc4449405ddff965392ceb8758a4209dac2b55`, [Draft PR #186](https://github.com/silverbjin/Pysical_AI_ROS2/pull/186). 실행 결과: GitHub Actions **FAIL** (의도한 기존 고장 유지), FJT Goal status=6/ABORTED, error=-5, 종료 `OWNED_GROUPS_EXITED_NO_SIGKILL`.

| 계측 경계 | 실제 결과 | 판단 |
|---|---|---|
| finger2 FJT 목표 | +0.011m, Goal tolerance 0.001m, time tolerance 2s | 목표 유효 |
| JTC `reference` 최대 | 0.011m, 450개 표본 | 제어 목표 생성 PASS |
| ros2_control **hardware `command_interface.joint_finger2/position`** 최대 | **0.011m** | 하드웨어 명령 인터페이스 전달 PASS |
| command `is_limited` | 전체 450표본 **0.0** | 인터페이스 제한 감지 없음 |
| command≥0.0105m 체류 | **211표본 / 2.10 simulation seconds** | 단발성 펄스가 아니라 지속 명령 |
| hardware `state_interface.joint_finger2/position` | 약 -3.03×10⁻¹⁸ ~ -2.48×10⁻¹⁸m | 위치 0m 고정 |
| hardware `state_interface.joint_finger2/velocity` | ±5.39×10⁻¹⁶m/s | 운동 없음 |
| JTC `feedback` / 독립 `/joint_states` | 사실상 0m | 하드웨어 상태와 일치 |
| Gazebo native `finger2` vs `link_wrist` 링크 이동 | **0m** | 실제 물리 링크 이동 없음 |
| Gazebo 원본 joint2 축 | `joint_finger2`: prismatic, `[-1,0,0]` | 축 식별 정확 |
| native finger 접촉 | 0건, 원통·지지대 없음 | 외부 물체 막힘이라는 설명 불가 |
| FJT 상태 | `ABORTED / -5` | 성공 허위 승격 차단 |

hardware introspection 전체 1,041개, 단일 Goal 구간 450개 유효 표본을 원본 JSON에 보존했다. Goal 종료 후 `reference/command`는 0으로 되돌아가기 때문에 **최종 한 건만 보면 제어 명령이 없었다고 오판**할 수 있다. 반드시 Goal 활성 시계열의 최고값·체류시간·timestamp를 사용해야 한다.

## 3. 장애 위치 및 원인 확정 수준

```text
FollowJointTrajectory Goal finger2=11mm     PASS
          |
JTC reference=11mm                         PASS
          |
controller_manager registered
  command_interface.joint_finger2/position  PASS — 실제 11mm
          |
gz_ros2_control/GazeboSimSystem position
  command → velocity control → physics
          X   <-- 이 내부 경계 미확정
native Gazebo finger2 prismatic motion      FAIL — 상대 위치 0m
          |
ros2_control state_position, state_velocity FAIL — 실제 운동 0
          |
/joint_states, JTC feedback                 약 0m (관측은 정상)
          |
FJT goal tolerance                          ABORTED -5 (판정 정상)
```

**입증된 원인 경계:** 목표 명령 누락, JTC 매핑·액션 성공 오판, controller-manager hardware **command interface 값 부재**, ROS State Publisher만의 표시 오류, 외부 원통 접촉 때문에 생긴 막힘은 이 단일 재현에서 제외된다. 따라서 오류는 **GazeboSimSystem의 position→velocity 구동 반영과 Gazebo 물리 엔진의 관절 운동 처리 사이**에 있다.

**아직 입증되지 않은 내부 원인:** GazeboSimSystem이 `JointVelocityCmd`를 작성하지 않거나 잘못 작성하는지, 명령은 작성했지만 물리 solver가 joint constraint/limit 또는 모델 내부 상호작용으로 이동을 거부하는지는 **구분 불가**. `command_interface`에 11mm가 등록된 것만으로 Gazebo ECS의 실제 velocity 명령까지 전달됐다고 단정하면 안 된다.

공식 문서에 따르면 Jazzy JTC의 position command는 하드웨어 command interface로 전달되고, `gz_ros2_control`은 position 오차를 내부 velocity 명령으로 환산한다. 참고: https://control.ros.org/jazzy/doc/ros2_controllers/joint_trajectory_controller/doc/userdoc.html 및 https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html.

## 4. 다음 최소 검증 — 현재 세션에서 반복 금지

무작위로 또 G04B 전체를 실행하지 말고, 필요한 경우 **하나의 새로운 Gazebo ECM 관측**만 추가한다.

1. 기존 실패 Goal 및 동일 q4에서 `joint_finger2` ECM의 `JointVelocityCmd` 시계열과 `JointPosition`/`JointVelocity`를 읽기 전용으로 채집한다. 시뮬레이터 내부 컴포넌트 접근 방법이 기존 도구로 지원되지 않으면 선행 소스 조사부터 한다.
2. 하드웨어 command 11mm인데 ECM velocity command 0/미생성 → **GazeboSimSystem write/매핑 단계 조사**. ECM velocity가 유한한 비영(非零) 값인데 실제 joint velocity=0 → **물리 solver·joint constraint 및 충돌 조건 조사**.
3. 이 분기 중 실제로 입증된 한 곳만 최소 TDD 수정하고 공개 CI 단일 냉시작으로 검증한다. 기존 G00~G04A 성공 재실행, 임의 게이트 약화, 원본 모델/관절축 변경, 물체 강제 attach/teleport는 금지.
4. 그 다음 양측 실제 접촉력, world Z≥0.05m 상승, 안정 유지≥1초, 물리 배치 ROI까지 증명된 경우에만 G04B를 인수한다. 이어서 G05 동일 세션 RGB-D→실제 물리 배치를 검증한다. Ch10은 HOLD이다.

## 5. TDD/CI 기록 및 판정

첫 observer 시도 [CI #43591101353](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43591101353)는 `introspection_data/full` publisher가 `BEST_EFFORT`인데 수신측이 `RELIABLE`이어서 자료를 받지 못했다는 QoS 경고를 원본에서 확인했다. 그 **관측기 경계만 수정**한 CI #43591347996에서 1,041개 hardware introspection 표본을 성공적으로 읽었다. 자체 static Python 구분 테스트 7/7 PASS; 실제 finger2 물리 구동은 RED 유지.

**최종 판정:** `COMMAND_DELIVERY_SCOPED_PASS`, `PHYSICAL_JOINT_ACTUATION_FAIL`, `G04B_BLOCKED`, `G05_NOT_RUN`, `Ch10_HOLD`. 원인 완전 규명이나 G04B 합격으로 승격 금지. Draft PR #186 미병합.
