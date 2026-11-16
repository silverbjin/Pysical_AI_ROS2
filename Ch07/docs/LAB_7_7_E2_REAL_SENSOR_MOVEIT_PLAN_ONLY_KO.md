# Ch07 §7.7 실습: 실제 RGB-D 목표 → MoveIt 계획, 물리 동작은 아직 금지
_강사·학생 공용 E1/E2 교재 | 2026-11-17 | Draft PR #204_

> 본 실습은 **Gazebo 실제 RGB-D에서 나온 3D 위치**를 ROS 2 미션 목표로 승인하고 **MoveIt plan_only**로 로봇팔 이동 경로를 계산하는 과정이다. **팔/그리퍼 구동 Goal은 0건**이며 실제 물체를 집었다는 뜻이 아니다. 물리 G04B와 전체 §7.7 E2E는 BLOCKED/NOT_RUN. Ch10 HOLD.

## 학습 목표

1. `sensor_msgs/Image`, `CameraInfo`, `/tf`가 왜 동일 촬영 시각·광학 좌표계여야 하는지 설명한다.
2. `/camera/target_pixel`의 z 성분은 **픽셀 면적(px²)**이지 Depth(m)가 아님을 구분한다.
3. `/camera/target_3d_base`의 `base_link` 좌표·stamp를 G01 `/ch07_77/target_ready`와 대조한다.
4. 목표 위치가 A→B로 이동하면 `mission_geometry.fixture_plan_targets`의 관절 계획도 바뀜을 직접 확인한다.
5. `MoveGroup.Goal.planning_options.plan_only=True`에서 계획 `SUCCEEDED`와 실제 로봇 움직임 `NOT_RUN`을 구분한다.
6. 독립 관찰자의 메시지 유실·시각 불일치가 원본 로봇 기능 실패와 다를 수 있음을 읽고 설명한다.

## 실제 소스 구조와 실행 흐름

```text
Gazebo OGRE2 dynamic red cylinder
  RGB /camera/image_raw + Depth /camera/depth/image_raw + CameraInfo + TF
      ↓
object_detector → /camera/target_pixel + /camera/target_valid
      ↓
coord_transformer → /camera/target_3d_base (PointStamped, base_link, metres)
      ↓
mission_controller + TargetGate → /ch07_77/target_ready (one-shot)
      ↓
mission_plan_only (NEW) ← mission_geometry (NEW, 24mm TEST-ONLY fixture)
      ↓
MoveGroup /move_action (plan_only=True, arm_group, no motor Goal)
      ↓
receipt: sensor stamp/xyz → pregrasp/approach/grasp joint targets → planned_points
```

**소스:** `Ch07/ros2_ws/src/vision_basics/vision_basics/{object_detector,coord_transformer,mission_controller,mission_target_gate,mission_geometry,mission_plan_only}.py`. `setup.py`의 실행 이름은 `mission_plan_only`. `ci/ch07_77_e2_rgbd_moveit_plan_once.sh`는 G04A의 검증된 Gazebo 실행 구성을 **같은 세션에 재사용**하며, 가짜 이미지나 world pose를 MoveIt Goal 입력으로 쓰지 않는다.

## 실습 순서

### 1. 학생의 최초 L0 실습 (ROS/Gazebo 불필요)

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git
cd Pysical_AI_ROS2
git fetch origin plan/ch07-77-rgbd-moveit-physical-e2e-20261117
git switch -c ch07-e2 --track origin/plan/ch07-77-rgbd-moveit-physical-e2e-20261117
python3 -m unittest discover -s ci/tests -p test_ch07_77_e2_sensor_moveit_contract.py -v
```

출력의 6개 테스트 PASS는 **수치·계약 L0만** 의미한다. 2개의 유효한 다른 센서 좌표로 만든 pregrasp/approach/grasp 관절 목표가 실제 달라지는지, NaN/Inf/범위 밖 입력에서 함수가 ValueError로 종료되는지 코드를 읽는다.

### 2. 강사 공개 CI 센서→MoveIt 관측 (실제 Gazebo headless)

[PR #204](https://github.com/silverbjin/Pysical_AI_ROS2/pull/204) Actions에서 `Book Ch07 E2 real RGB-D sensor to MoveIt PLAN ONLY`의 상태와 Artifacts를 확인한다. **실제 실행이 이미 성공했다는 의미로 녹색을 추정하지 않는다.** 실행기가 초기화되면 `ci-results/ch07-77-e2/`에 다음 항목을 남긴다.

- `g04a_live_receipt.json`: RGB/Depth/K/target_pixel/target_3d_base/target_ready의 시각과 frame
- `e2_moveit_plan_receipt.json`: 실제 G01 target stamp/xyz → 3개 sensor-derived wrist/joint requests → 각 계획 status/points, motor Goal 0
- `coord.log`: 실제 3D 변환 노드가 발행한 `CH07_75_VALID_3D_TARGET stamp=...` 라인
- `move_group.log`, `controllers_after.log`: 실제 MoveIt server·GazeboSimSystem 구성
- `result.json`, `stages.log`: 최초 실패/최종 프로세스 종료. **SIGKILL_ESCALATION이면 전체 Run FAIL**로 유지

동일 표적이라도 관찰용 DDS 노드가 지연 구독하면 첫 `target_3d_base` 메시지를 놓칠 수 있다. 관찰기 결과를 덮어쓰지 말고, **원본 `coord.log`의 stamp/XYZ, 실제 optical pixel, G01 ready, E2 target/Goal의 값을 교차 대조**한다. 이는 시각 불일치를 우회하는 합격 트릭이 아니라 **실제 센서에서 발생한 목표의 인과관계를 증명하기 위한 별도 독립 판정**이다.

### 3. 실제 ROS 토픽·Action 탐색 (인수된 실습 환경에서만)

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic info -v /camera/target_3d_base
ros2 topic echo /camera/target_3d_base --once
ros2 topic echo /ch07_77/target_ready --once
ros2 action info /move_action
ros2 control list_controllers
```

토픽이 안 보인다면 노드가 실행 중인 세션인지 먼저 확인한다. 기존 CI와 달리 원격 PC에서 아무 Goal을 수동 전송하지 않는다. ROS_DOMAIN_ID와 GZ_PARTITION을 다른 세션과 공유하지 않는다.

## 교육용 해설·리뷰 과제

- **정적 상태:** 성공한 `MoveGroup` Action이 왜 로봇이 실제 움직였다는 증거가 아닌가? `planning_options.plan_only=True`와 각 단계의 `planned_points`를 근거로 설명한다.
- **좌표계:** 실제 3D 표면점과 원통 중심·손목(조인트 FK)·손끝(TCP)의 차이를 그림으로 정리한다. E2 `FixtureCalibration`의 offset은 이전 물리 시험의 **계산 후보**이므로 파지를 승인하는 자동 교정이 아니다.
- **안전:** detector가 사라지거나 Depth가 NaN/TF가 오래되었을 때 신규 모터 Goal은 0이어야 한다. G01과 E2의 어느 단계에서 차단되는지 코드로 설명한다.
- **고장 분석:** G04A witness의 `MISSION_TARGET_NOT_FROM_SENSOR`가 실제 detector 결함인지, DDS 수집 시각 누락인지 **pixel → coord 로그 → G01 ready → E2 goal**로 원본을 대조한다.

## 다음 단계의 엄격한 경계

이번 실습은 `E2_SENSOR_TO_PLAN`까지만이다. E3에서 별도의 **실제 Gazebo physical grip/lift/hold/release/settled ROI + 금지 손목 충돌 0**가 독립 감사로 통과해야만, E4의 같은 세션 **인식→계획→구동→물체 이동**을 정식 인수할 수 있다. C17은 bin 테스트월드·손목 충돌이 포함된 교육용 실패 사례이며 **G04B PASS로 승격 금지**. 물리 성공 전에는 Owner WSL2 인수를 시작하지 않는다.
