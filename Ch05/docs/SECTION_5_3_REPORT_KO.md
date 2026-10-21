# 5.3절 코드 리뷰 — JointTrajectory 개루프 각도 명령

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 실제 동작 계약
- 실제 구현: manipulation_basics/simple_joint_controller.py(클래스 SimpleTrajectoryPublisher); setup.py 실행명 simple_controller.
- 원고의 simple_trajectory_publisher.py는 파일로 존재하지 않는다. 이 명칭으로 엔트리포인트를 고치면 ModuleNotFoundError가 발생한다.
- 2초 타이머마다 joint1~joint4에 [0, 0.5, 0.5, 1.0]과 [0,0,0,0] rad를 교대로 한 점 trajectory로 보내며 목표 시각은 1초다.
- 명령 관절 이름은 controller YAML·URDF와 텍스트 일치(TC01·TC02 PASS). 위 각도는 URDF joint limit 안쪽이다(수치 대조, 실제 동력학 미검증).

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-10 | HIGH | 원고: simple_trajectory_publisher.py / setup.py 목표 import가 실제 코드와 다름 | 독자가 본문 그대로 작성·설정하면 모듈 로드 실패. 실제 simple_joint_controller.py로 일원화 |
| C05-11 | HIGH | 원고: source install/setup. 및 source ~/ros2_ws/install/setup.ros2, run manipulation_basics simple_controller | 유효하지 않은 셸·ROS CLI 구문. source install/setup.bash → ros2 run manipulation_basics simple_controller |
| C05-12 | MEDIUM | 시작 시 /arm_controller/joint_trajectory subscriber와 active 상태를 확인하지 않음 | 토픽에 메시지가 publish되더라도 동작하지 않을 수 있음. 상태 검사 및 목표/실측 비교 필요 |
| C05-13 | MEDIUM | 원고의 '개루프' 표현 | 상위 publisher는 피드백 미사용이지만 하위 JointTrajectoryController, Gazebo 모터 제어 동작과 구분해야 함 |
| C05-14 | MEDIUM | 시간 1초는 동작 목표 시각일 뿐 실제 속도 한계/부드러움을 자동 보장하지 않음 | 제어기 보간, 부하, 물리 스텝, 시작 상태에서 추종오차 검증 필요 |

## 3. 정적 검사·미검증
- TC01: entry_points 실파일 매칭 PASS; TC02: 4개 joint 정적 매칭 PASS.
- 미수행: ROS 2 노드 실행, trajectory 수신, Gazebo 움직임, 추종 오차/가속도 측정.
- 실행 게이트: ros2 control list_controllers 결과 arm_controller active; ros2 topic info /arm_controller/joint_trajectory -v에 적어도 1 subscriber.
- 실행 관찰: ros2 run manipulation_basics simple_controller 후 ros2 topic echo /arm_controller/joint_trajectory --once와 /joint_states를 비교한다.

## 4. 승인 기준
1. 원고의 소스명·CLI를 실제 패키지에 맞게 정정.
2. 동일한 joint 이름에 대한 목표·측정값을 2주기 이상 관찰하고 관절별 오차를 기록.
3. 제한 범위 밖 명령은 **자동 차단된다고 가정하지 말고** 실제 컨트롤러의 오류·설정·안전 경로를 검증.
4. simple_controller와 wave_hello를 동시에 실행하지 않음(동일 제어기 명령 충돌).

**판정: SOURCE STATIC PASS / MANUSCRIPT COMMANDS FAIL / MOTION NOT VERIFIED.**

---
대응 실습: [LAB_5_3_GUIDE_KO.md](LAB_5_3_GUIDE_KO.md)
