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
