# SECTION_7_7_REPORT_KO — 인식 기반 pick-and-place 전체 파이프라인 구축

> 기준일: 2026-10-20 (KST) · 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 · 기준 브랜치: main
> 원고: 사용자가 첨부한 「7장. 물체 인식 및 조작」의 7.7절
> 판정: **BLOCKED — 미션 소스 존재하지만 end-to-end 계약 단절**
> 검증 등급: **STATIC_REVIEW_ONLY** (원격 GitHub 소스 확인 및 명시적 문자열·계약 점검, ROS 2/Gazebo 실행 테스트 아님)

## 1. 목적과 범위
Ch12의 가이드/절별 보고서 분리 원칙을 따라 **구현된 사실과 권장 수정, 실측 결과와 예상 결과**를 구분한다. 원고 예시는 본문의 교육 설계 기준이며, 명령어와 실제 코드가 다른 경우에는 저장소를 우선해 판정한다. 이 보고서는 문서/코드 리뷰 결과이며 실제 코드 수정 완료를 뜻하지 않는다.

## 2. 확인한 실제 소스
- [Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/mission_controller.py)
- [Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/object_detector.py)
- [Ch07/ros2_ws/src/vision_basics/vision_basics/gripper_controller.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/vision_basics/gripper_controller.py)
- [Ch07/ros2_ws/src/vision_basics/setup.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/vision_basics/setup.py)
- [Ch07/ros2_ws/src/my_robot_moveit_config/config/my_robot.srdf](https://github.com/silverbjin/Pysical_AI_ROS2/blob/a318c04a69a003e5c5d5998f077f2b8a8f36a1a5/Ch07/ros2_ws/src/my_robot_moveit_config/config/my_robot.srdf)

## 3. 핵심 발견사항(심각도 기준)
1. **[BLOCKER] detector는 /camera/target_pixel(PointStamped)을 발행하지만 mission_controller는 /robot/target_position을 구독하지 않는다.** 대신 TF 이름 target_object를 직접 조회하며, 이 TF를 만드는 노드의 연결은 확인되지 않는다.
2. **[BLOCKER] mission_controller.execute_pick_and_place(t_x,t_y,t_z)는 검출한 target을 받은 뒤 실제 이동에 하드코딩된 self.move_arm(1.0,...), self.move_arm(0.90829,...), self.move_arm(1.1,...)을 사용한다.** 검출 기반 pick-and-place 성공 증거가 아니다.
3. **[HIGH] 미션이 끝난 뒤 is_working=false가 되면 target_object TF가 남아 있는 한 다음 타이머에서 같은 미션을 재실행할 수 있다.** one-shot/목표 ID/신선도·상태 전이 규칙이 필요하다.
4. **[HIGH] /compute_ik, /move_action, gripper server 무한 wait 및 future 반복 폴링에 타임아웃/취소가 없다.** 서버 누락·종료 시 무기한 멈출 수 있다.
5. **[HIGH] 그리퍼 goal이 accepted 되어도 action result/관절값/실물 파지 여부를 확인하지 않고 다음 상태로 진행한다.** 하강 충돌·미파지·떨어뜨림을 성공 처리할 위험.
6. **[HIGH] setup.py에 mission_controller 등록이 없다.** 코드에 FSM 주석은 있지만 실질 상태를 독립 분리한 단계별 검증/복구가 미흡하다.
7. **[MEDIUM] MoveIt SRDF에 arm_group/gripper_group은 있지만 collision disable이 광범위하다.** 실제 로봇 링크 간 충돌 여유를 별도로 시험해야 한다.

## 4. 수정 권고 및 교육 설계
- 7.4 PointStamped→7.5 3D PointStamped→미션 구독의 타입·frame·stamp를 통일하고 target_object TF 방식 사용 여부를 결정한다(양쪽 병행 사용 금지).
- 목표 좌표를 pregrasp/grasp/retreat 단계의 상대 목표로 실제 전달하되 그리퍼/TCP 오프셋 및 IK/충돌 검사 결선한다.
- IDLE→DETECT→PLAN→APPROACH→GRASP→VERIFY_GRASP→LIFT→PLACE→VERIFY_PLACE→DONE/RECOVERY FSM, 1회 트리거와 재실행 조건을 구현한다.
- 서버/액션/TF/센서 타임아웃, stage별 error_code, 중지·복귀·로그를 적용한다.
- 실물 이동이 아니라 Gazebo 기준 물체 pose가 잡기→들기→놓기 동안 올바르게 변했는지 근거로 성공을 판정한다.

## 5. 테스트·Evidence
- **수행:** mission_controller.py/object_detector.py/gripper_controller.py/setup.py 및 SRDF 정적 교차 분석.
- **확인:** target_object TF 의존과 PointStamped 발행의 연결 단절, 하드코딩된 x/y/z, 반복 트리거·무기한 대기·grasp 판정 공백.
- **미수행:** ROS/Gazebo/MoveIt 통합, 실제 물체 이동·파지·배치 성공 실험.

### 재검증 체크리스트
- [ ] source 환경 충돌 제거 및 colcon build로 해당 패키지 설치 확인
- [ ] ros2 pkg executables/launch, 직접 의존성, 토픽 타입/QoS/네임스페이스 검사
- [ ] 관련 절의 정상/실패 입력에 대한 단위·정적 회귀 테스트
- [ ] Gazebo Harmonic + ROS 2 Jazzy에서 실제 런치, 로봇 동작/종료 확인
- [ ] 터미널 명령·exit code·토픽/TF/액션·화면/CSV의 원본 Evidence 확보
- [ ] Ch07 단독 overlay에서 실행하고 이전 장 패키지 설치경로 섞임 확인

## 6. PR 판단
**문서 리뷰 PR은 검토 가능, 해당 절 실습이 이미 정상 실행된 것으로 승인 불가.** 실습 가이드의 명령 중 선행 수정 조건이 있는 단계는 수정 후에만 진행한다. 수정·시험을 완료하면 이 파일의 STATIC_REVIEW_ONLY 상태를 실제 결과로 교체해 재심사해야 한다.

관련 문서: [LAB_7_7_GUIDE_KO.md](LAB_7_7_GUIDE_KO.md).
