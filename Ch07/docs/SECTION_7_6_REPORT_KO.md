# Ch07 §7.6 — 실제 Gazebo 두 손가락 제어 검수 보고서

> **최종 갱신:** 2026-11-13 KST · **판정: 범위 한정 PASS (두 개의 독립 CI 증거)**.
> 이 보고서 아래에 보존된 2026-10-20 정적 분석은 당시 상태의 기록이며, 2026-11-13 실제 실행 검수로 변경된 항목을 우선한다.

## 2026-11-13 실제 실행 결과

| 경계 | 최종 판정 | 원본 증거 |
|---|---|---|
| 실제 GazeboSimSystem 및 그리퍼 JointTrajectoryController 활성화 | PASS | 공개 CI [#43354355284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354355284), Artifact 14005852131 |
| 두 prismatic 관절 열기 → 완료 → 닫기 → 완료, 각 관절 피드백 확인 | PASS | 동일 실행 (단, 해당 **전체 CI job은 종료 문제로 FAIL**) |
| 독립 ROS 관절 상태 최종 위치 | PASS | 동일 실행, 15개 관절 메시지 |
| Gazebo/RSP/브리지 소유 프로세스 그룹 정상 회수 | PASS | 별도 종료 전용 공개 CI [#43358805356](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358805356), Artifact 14007780496 |
| 실제 물체 접촉·마찰 조절·잡기·리프트 | NOT_RUN | 시뮬레이터 물체/접촉 판정 미검수 |
| Ch07 §7.2 실제 RGB-D 입력 | BLOCKED | Issue #127, OGRE2 SIGABRT |
| WSL2 GUI 및 실물 하드웨어 | NOT_RUN | 현장 인수 미진행 |

### 실제 관절 계측 수치

- **OPEN:** 두 관절 각각 0.00500m 목표, 최대 오차 **0.000250m**, 관측 위치 약 **0.004750m**.
- **CLOSE:** 두 관절 각각 0.02000m 목표, 최대 오차 **0.000499m**, 관측 위치 약 **0.019501m**, 관측 이동량 **0.014726m**.
- **독립 계측:** 두 손가락 최종 위치 약 **[0.0199992737m, 0.0199992737m]**, 관절 메시지 15개.
- 제어 경로: \`/gripper_group_controller/follow_joint_trajectory\` (control_msgs/action/FollowJointTrajectory), \`joint_finger1\`·\`joint_finger2\`; 관절 단위 **미터(m)**. 각 Action은 실제 Gazebo 컨트롤러에서 \`SUCCEEDED\`를 반환했다.
- 기능 검증 소스 \`c619a7aabb2f1bd2c781d757275d66f8ba89851a\`와 최종 종료 검증 소스 \`2e718a55e38dd3c1d2a7970b9b2e920c96f901b7\`의 **\`gripper_controller.py\` blob SHA는 동일**: \`1c104193f29940ba565cc3a32cd35c5bf4e51f38\`.
- 기존 고정 Docker runtime digest 유지: \`sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f\`. 새로운 Docker 이미지나 월드를 만들지 않았다.

### 오래 걸린 종료 실패의 원인과 해결

첫 실패 [#43354159858](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354159858)는 URDF 안의 **주석 문자열** \`FakeSystem\`을 실제 하드웨어로 오인한 정적 검수기 문제였다. 실제 Gazebo 하드웨어 확인으로 검사 경계를 옮겼다.

그 뒤 [#43354355284](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43354355284)는 모든 그리퍼 액션과 피드백이 성공했으나 전체 Job은 외부 종료 제한 시간 \`rc=124\`로 FAIL이었다. 종료 전용 [#43356270466](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43356270466)도 같은 실패를 보여 액션 실행과 종료 문제가 독립임을 확인했다.

[진단 CI #43358336634](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358336634), Artifact 14007625114에서 원인을 확정했다. 상위 \`cleanup()\`의 역순 카운터 \`i\`와 하위 \`stop_owned()\`의 \`for i in ...\`가 **Bash 동적 스코프**를 통해 충돌했다. 하위 루프의 \`i\` 변경으로 상위 루프 인덱스가 계속 0으로 되돌아가 PID 84 회수가 반복되는 무한 루프였다.

해결은 하위 카운터를 **\`local attempt\`로 분리**한 최소 수정이다. 기능 코드는 변경하지 않았다.

[종료 전용 성공 CI #43358805356](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43358805356)의 실제 원본 Artifact 14007780496에서는 세 소유 프로세스 그룹이 역순으로 **172 → 86 → 83**, 각각 **단 한 번** 처리됐다. 모두 SIGTERM으로 종료되고 SIGKILL 승격 없이 \`result.json\`이 다음과 같이 기록되었다.

~~~json
{
  "status": "TEARDOWN_SCOPE_PASS",
  "rc": 0,
  "shutdown": "PROCESS_GROUPS_EXITED_AFTER_SIGTERM",
  "action_retest": "NOT_RUN"
}
~~~

**증거 판정 한계:** 성공한 기능 시험과 성공한 종료 시험은 **서로 다른 CI run**이다. 최종 수정 후 *한 실행에서* 열기·닫기와 정상 종료를 동시에 다시 시험하지 않았으므로, 단일 end-to-end CI 성공을 주장하지 않는다. 종료 후 프로세스 목록에 소유 그룹 외의 Python 프로세스가 남았으므로, 모든 컨테이너 자식이 사전 종료됐다는 주장도 하지 않는다. 다만 Docker 실행은 rc=0으로 완료됐고 소유한 Gazebo·브리지·RSP 그룹은 정상 회수되었다.

## 다음 작업 및 재검 정책

- **Ch07 §7.6 MVP 제어 경계 종료:** 위의 두 CI 원본 결과를 조합한 범위 한정 PASS. [PR #142](https://github.com/silverbjin/Pysical_AI_ROS2/pull/142) main 병합 SHA \`97e1e1a4a5dc8a37d226a80c026c9c1c0783d155\`.
- 앞으로 **그리퍼 소스/모델/검수기가 달라질 때**에만 실제 open→close 전체 CI를 돌린다. 이번에 성공한 액션은 같은 소스에서 재실행하지 않는다. 종료만 분석할 때는 CI 수동 실행의 \`teardown_only\` 모드를 사용한다.
- Ch07 §7.7 전체 pick-and-place는 실제 카메라, 3D 정렬, 파지와 리프트 증거가 없으므로 BLOCKED 유지.
- Ch11 원본 slam_toolbox SaveMap Service #130은 FAIL 유지(공식 Nav2 CLI 별도 PASS), Ch10 #123 HOLD.

---

## 2026-10-20 정적 검토 원본 (이력 보존)

# SECTION_7_6_REPORT_KO — 그리퍼 제어와 파라미터 튜닝

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.6절
> 판정: **BLOCKED — 제어 노드 존재, 시뮬레이터 실행·물리 파지 미검증**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/vision_basics/gripper_controller.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/gripper_controller.py)
- [Ch07/ros2_ws/src/vision_basics/config/ros2_controllers.yaml](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/config/ros2_controllers.yaml)
- [Ch07/ros2_ws/src/my_robot_moveit_config/config/ros2_controllers.yaml](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/my_robot_moveit_config/config/ros2_controllers.yaml)
- [Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/urdf/my_robot.urdf.xacro)
- [Ch07/ros2_ws/src/vision_basics/urdf/my_robot.ros2_control.xacro](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/urdf/my_robot.ros2_control.xacro)

## 3. 핵심 발견사항(심각도 기준)
1. **[HIGH] 실제 그리퍼 액션 명은 /gripper_group_controller/follow_joint_trajectory이고 목표 조인트는 joint_finger1/2 두 개**다. 원고의 /gripper_controller/follow_joint_trajectory 및 단일 gripper_joint와 불일치. 이 모델의 prismatic 조인트 단위는 **m**이며 rad이 아니다.
2. **[BLOCKER] vision_basics/urdf/my_robot.urdf.xacro에서 ros2_control include와 Gazebo 플러그인이 주석 처리되어 있다.** 독립 Gazebo 제어가 자동으로 활성화된다고 말할 수 없다.
3. **[HIGH] 두 개의 ros2_controllers.yaml에 gripper 컨트롤러 타입이 다르다.** vision_basics/config는 JointTrajectoryController, my_robot_moveit_config/config는 parallel_gripper_action_controller. 실제 로드된 설정이 무엇인지 확인하지 않으면 액션 타입이 다를 수 있다.
4. **[HIGH] gripper_controller.py의 main은 open, sleep(3), close 호출 후 spin을 시작한다.** send_goal_async 콜백 실행 시점이 늦어지고, 첫 goal이 종료되기 전에 다음 goal을 보낼 수 있다. 반환 상태/오류/시간 초과도 충분히 평가하지 않는다.
5. **[HIGH] 원고의 물리 파라미터 gripper_left_finger_link는 실제 URDF finger1/finger2와 명칭 불일치.** 원고의 매우 큰 mu와 kp는 Harmonic에서 충돌 backend/마찰 모델에 따른 차이가 커 그대로 권장할 수 없다.
6. **[MEDIUM] get_result_callback의 출력만으로 물체가 실제로 파지되었다고 말할 수 없다.** 관절 위치, 접촉 및 물체 높이/상대변위가 필요하다.

## 4. 수정 권고 및 교육 설계
- Gazebo Harmonic + gz_ros2_control 시스템 플러그인·관절 인터페이스 활성화 여부를 실제 launch로 검증한다.
- 제어기 설정 원본을 하나로 결정하고 ROS action list -t와 ros2 control list_controllers로 종류/상태를 확인한다.
- goal send→accepted→result→error_code까지 순차 대기 및 제한 시간·취소/실패 처리를 구현한다.
- 마찰·접촉값은 1회에 변수 하나만 바꾸는 sweep 실험으로 튜닝하며 ODE/SDFormat/엔진 차이를 확인한다.
- open/close 방향과 값은 joint_limits 및 실제 finger 간격으로 검증하고 파지 성공은 물체 lifting으로 판정한다.

## 5. 테스트·Evidence
- **수행:** 액션 이름/조인트 배열, 두 제어기 yaml의 타입 차이, URDF prismatic limits, ros2_control 주석 및 비동기 흐름 정적 대조.
- **확인:** 메시지 계약 불일치, 제어 플러그인 비활성화, 타입 충돌 후보, 목표 종료 전 순차 명령 위험.
- **미수행:** Gazebo 물리 접촉/실제 제어기 상태 확인 및 그리핑 성공률 측정.

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_6_GUIDE_KO.md](LAB_7_6_GUIDE_KO.md).
