# 13.6 Go2+Piper 정밀 조작 실습

현재 개발 중인 가이드다. 최종 인수 보고서의 PASS UUID와 freeze를 확인하기 전 물리 파지 검증 완료판으로 사용하지 않는다.

## 준비

이 실습은 Ubuntu 24.04/WSL2, ROS 2 Jazzy, MuJoCo 3.13.0, 원본 IIT-DLSLab 정책과 94개 고정 자산을 사용한다. 원본 모델·mesh·가중치는 Git 저장소에 재배포하지 않는다. 먼저 [13.5 다운로드·가상환경 가이드](LAB_13_5_REUSE_GUIDE_KO.md)의 소스 다운로드와 자산 해시 확인까지 수행한다. 다른 로봇의 MoveIt 설정이나 과거 Task8 checkout을 사용하지 않는다.

13.6 소스 branch는 `feat/ch13-section-13-6-manipulation`이다. main에 병합된 것으로 가정하지 않는다. 저장소 루트가 현재 위치인지 확인한다. 아래 Linux 명령의 작업 위치는 모두 그 저장소 루트다. 이미 실행 중인 엔진이 있으면 소유 mission에서 정상 회수한 다음 진행한다.

기존 추론 환경은 `/home/jinho/ch13_reuse_iit_d010212_venv`, 이 실습 전용 build는 `/home/jinho/ch13_reuse_13_6_build`다. 다른 경로를 쓰면 모든 터미널에 `CH13_REUSE_VENV`와 `CH13_REUSE_BUILD`를 동일하게 지정한다. R2/R5 build를 덮지 않는다. ROS CLI는 시스템 Python, 시뮬레이터는 지정 venv를 사용한다. 추론 venv를 터미널 전체에 activate하지 않는다.

MoveIt 2.12.4, moveit_msgs 2.6.0, TRAC-IK 2.0.2가 검증 환경에 이미 설치돼 있었다. 새 환경에서는 ROS 공식 패키지 관리로 MoveIt·TRAC-IK·colcon 의존성을 준비한 뒤 실제 버전을 확인해야 한다. 이번 개발에서 apt/pip 설치·시스템 라이브러리 변경은 하지 않았다. 버전이 다른 경우 원고의 개념 코드를 그대로 실행하지 말고 설치 API와 이 패키지의 계약을 확인한다.

```bash
source /opt/ros/jazzy/setup.bash
dpkg-query -W ros-jazzy-moveit ros-jazzy-moveit-py ros-jazzy-trac-ik-kinematics-plugin ros-jazzy-moveit-msgs
bash Ch13/scripts/reuse_13_6/build.sh
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/run_tests.py
```

빌드는 6개 패키지를 선택하고 통합 MuJoCo 모델에서 URDF/SRDF를 로컬 생성한다. 외부 자산 hash가 다르면 중단한다. 시뮬레이션 실행 중 build나 pytest를 병행하지 않는다.

## 13.6.1~2: 같은 엔진의 인계와 계획 장면

13.5 단독 실행을 끝낸 뒤 팔 노드를 새로 붙이는 방식이 아니다. 아래 mission은 Nav2 접근·실제 정착·원본 관측을 확인한 바로 그 엔진을 유지한다. 과거 summary의 READY는 작업 권한이 아니다. 한 번에 한 명령만 실행한다. 각 증거 경로는 존재하지 않는 새 이름이어야 한다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh hold Ch13/evidence/section_13_6_reuse/my_hold_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_handoff.py Ch13/evidence/section_13_6_reuse/my_hold_01
```

기대 결과는 동일 session에서 2wall초 이상 READY 유지, 명시 REVOKED, 엔진·RX·renderer·원본 thread join과 잔여 없음이다. 접근 중 VISION_EXPIRED가 발생하면 실패 증거를 보존한다. 기준을 낮추거나 과거 JSON으로 우회하지 않는다.

계획 장면에는 ground plane, 벽과 받침, 관측 대상 형상을 넣는다. 다리·팔 실제 joint_states와 실제 몸체 TF를 사용한다. planning group은 `manipulator_arm`, TCP는 `reuse/tcp`, base는 `reuse/base`다. MoveIt는 별도 joint_states/TF 발행자가 아니다. TRAC-IK와 OMPL RRTConnect로 계획한다.

## 13.6.3: 좌표와 원본 시각

실제 카메라의 320×240 RGB-D와 촬영 시점 이전 100ms 이내 TF를 사용한다. `last_accepted_observation.json`에는 optical point, map point, T_map_camera, calibration, capture/receipt/GID와 내용 hash가 있다. 최신 TF로 과거 이미지를 변환하거나 header를 now로 바꾸지 않는다. map↔odom은 현재 교육 profile의 ground-truth localization이다. SLAM/AMCL 성공을 뜻하지 않는다.

13.5의 붉은 상자는 보이는 표면점이다. 물리 파지 profile에서는 알려진 upright 원통 반경 2cm·높이 8cm와 RGB-D 표면 fit으로 중심을 추정한다. yaw나 일반 물체 6D pose를 관측한 것이 아니다. 실제 freejoint 위치는 실행 후 평가 파일에만 기록한다.

## 13.6.4~5: 계획·실행과 픽킹

먼저 작은 팔 시험과 MoveIt 도달/거절/직선/취소 시험을 수행한다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh arm_normal Ch13/evidence/section_13_6_reuse/my_arm_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_arm.py Ch13/evidence/section_13_6_reuse/my_arm_01
bash Ch13/scripts/reuse_13_6/run_case.sh moveit Ch13/evidence/section_13_6_reuse/my_moveit_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_moveit.py Ch13/evidence/section_13_6_reuse/my_moveit_01
```

원고의 `plan().execute()`/`compute_cartesian_path()`는 개념 코드다. 실제 [Python 래퍼](../ros2_ws/src/ch13_manipulation_reuse/ch13_manipulation_reuse/planning.py)는 단일 MoveIt 장면의 GetMotionPlan/GetCartesianPath와 기존 엔진의 FollowJointTrajectory를 사용한다. 이 버전의 ExecuteTrajectory 취소 문제 때문에 그것과 병렬로 실행하지 않는다. 장면 hash·실제 시작 관절·관측 age를 재확인하고 전체 Cartesian fraction=1만 허용한다. 0.9는 충분하지 않다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh pick Ch13/evidence/section_13_6_reuse/my_pick_01
bash Ch13/scripts/reuse_13_6/env.sh Ch13/scripts/reuse_13_6/verify_pick.py Ch13/evidence/section_13_6_reuse/my_pick_01
```

동일 엔진에서 open→12cm pre-grasp→직선 접근→close→양 finger 실제 접촉→직선 10cm lift→2초 hold→작업 후 정착·회수를 수행한다. 대상은 20g 동적 원통이며 원본 gripper cap 0.5N을 유지한다. planning scene attach는 충돌 표현이며 물리 부착이 아니다. 판정은 실제 상승≥9cm, 2sim초 이상 유지, TCP에 대한 상대 변화≤2cm, HOLD 중 90% 이상 양 finger 접촉으로 한다. `pick_assessment.json`과 독립 verifier가 PASS여야 한다. 팔 action 성공이나 빈 그리퍼 close만으로 파지 성공이라고 해석하지 않는다.

## 13.6.6~7: 안정성·실패·종료 판독

속도·가속도 scaling은 0.08, native trajectory 한계는 0.05rad/s·0.1rad/s²다. 다리는 기존 정책으로 계속 지지한다. torso 고정/teleport나 새 WBC·재학습으로 대체하지 않는다. 팔에는 원본 Kp/Kd·힘 cap을 유지한 명시적 모델 bias 보정 v2가 사용된다. [설계 변경 기록](SECTION_13_6_REUSE_ENGINEERING_DECISIONS_KO.md)을 읽는다.

도달 불가·충돌 거절은 팔을 실행하지 않아야 한다. Cartesian fraction<1은 pre-grasp나 목표 자세를 재검토할 이유이며 부분 경로를 실행하지 않는다. 접촉 허용은 지정 finger-target 쌍만 단계에 따라 변경한다. 전체 padding/충돌 검사를 꺼서 성공시키지 않는다.

```bash
bash Ch13/scripts/reuse_13_6/run_case.sh arm_cancel Ch13/evidence/section_13_6_reuse/my_cancel_01
bash Ch13/scripts/reuse_13_6/run_case.sh arm_loss Ch13/evidence/section_13_6_reuse/my_loss_01
bash Ch13/scripts/reuse_13_6/run_case.sh duplicate Ch13/evidence/section_13_6_reuse/my_duplicate_01
```

취소 ACK와 실제 terminal을 구분한다. fault/cancel은 제한된 감속·hold로 이어지며 torque0/무조건 수납·파지 중 임의 개방하지 않는다. 관측 300ms 초과·시계 역행·중복 소유자는 fault latch다. 입력이 복구돼도 자동 재활성화하지 않는다. 실행 도구는 계획기를 살아 있는 엔진 시계에서 먼저 회수하고 엔진을 정상 종료한 뒤 자식·renderer·lock 잔여를 확인한다. 강제 종료가 발생한 실행은 정상 회수 PASS로 세지 않는다.

새 실행을 만들기 전에 실패 폴더를 지우지 않는다. 다른 기존 engine이 검출되면 실행을 멈추고 그 소유 mission에서 회수한다. 오래된 PID 파일만 보고 프로세스를 죽이거나 lock 파일을 삭제하지 않는다.
