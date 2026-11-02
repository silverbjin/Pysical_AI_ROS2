# 5.2절 코드 리뷰 — Gazebo Harmonic과 ros2_control 실행 파이프라인

> 기준: 2026-10-20 KST, main @ 1b9e8215e2130c492969bb0da52a82e707c3a16f.
> 범위: 원고 5장 및 Ch05/ros2_ws/src/manipulation_basics. ROS 2 Jazzy / Ubuntu 24.04 / Gazebo Harmonic을 목표 환경으로 한다.
> 방법: GitHub 원격 소스 열람 + 경로/문자열 기반 정적 일관성 검사(12건, PASS 7 / FAIL 5). ROS 2·Gazebo 실행, colcon build, pytest, GUI, 실제 운동/오차 측정은 이 실행 환경에서 **수행하지 못함**. 정적 PASS를 동작 PASS로 해석하지 않는다.
> 이 브랜치는 문서만 추가하며 원본 코드를 수정하지 않는다. 5.1~5.6절 브랜치는 모두 동일한 main 기준 독립 PR 대상이다.

## 1. 파일·경로 대조
- launch/manipulation_system.launch.py는 xacro.parse + process_doc으로 robot.urdf.xacro를 처리하고 ros_gz_sim/gz_sim.launch.py에 -r empty.sdf를 넘긴다.
- urdf/robot.urdf.xacro는 robot.ros2_control.xacro를 include하고 gz_ros2_control-system 플러그인을 설정한다.
- ros2_controllers.yaml의 4개 arm joint와 URDF의 4개 위치/상태 인터페이스는 정적으로 대응한다(TC02 PASS).
- launch에는 robot_state_publisher, ros_gz_sim create, controller_manager spawner, /clock 브리지, RViz 노드가 모두 선언되어 있다(TC05·TC12 PASS).

## 2. 발견사항
| ID | 심각도 | 근거 | 영향 / 권고 |
|---|---|---|---|
| C05-05 | HIGH | OnProcessExit(spawn_entity) 후 JSB 실행; JSB 프로세스 OnProcessStart에서 고정 TimerAction(2.0초) 후 arm_controller 실행 | spawn의 **성공 종료**, controller_manager의 준비 완료, JSB의 **active 상태**를 검사하지 않음. 느린 WSL/Gazebo에서 실패/경쟁 가능. 실제 서비스 readiness·명시적 timeout·실패 처리 필요 |
| C05-06 | HIGH | package.xml에 ros_gz_bridge, xacro, robot_state_publisher, gz_ros2_control 등 실행 의존성 일부 누락 | 깨끗한 ROS 환경에서 launch import/플러그인 미발견 위험 |
| C05-07 | MEDIUM | world 링크와 world_to_base_joint fixed로 기본 모델 기준이 고정됨 | 물리 바닥 접촉/실제 이동을 기대한 설명과 구별. spawned entity의 물리 자세와 TF 관계 실측 필요 |
| C05-08 | MEDIUM | 문서의 source install/setup.ros2 launch ... 구문 | 쉘 명령 오류. source install/setup.bash 다음 ros2 launch로 분리해야 함 |
| C05-09 | MEDIUM | Gazebo create의 종료 코드가 성공인지 확인하지 않고 종료 이벤트에 반응 | 실패해도 스포너 단계로 전이 가능 |

## 3. 검사·재현
- TC02/TC03/TC05/TC12 정적 PASS; TC09(고정 시간 의존) FAIL.
- 사용 가능한 ROS/GUI가 없어 xacro 실제 변환, gz 플러그인 로드, controller_manager 접속, /clock 동작은 **미검증**.
- 재현: cd Ch05/ros2_ws → colcon build --symlink-install --packages-select manipulation_basics → source install/setup.bash → ros2 launch manipulation_basics manipulation_system.launch.py.
- 다른 쉘: ros2 control list_controllers; ros2 topic echo /joint_states --once; ros2 topic hz /clock; ros2 topic info /arm_controller/joint_trajectory.
- 기대: joint_state_broadcaster와 arm_controller가 각각 active. 빈 로그나 inactive는 성공이 아니다.

## 4. 권장 수정·회귀 시나리오
1. 스포너가 controller_manager 서비스 준비 및 JSB 활성화를 확인하도록 순차 실행하고, 실패 시 오류 코드/로그를 남긴다.
2. Gazebo를 느리게 실행하거나 2초 이상 초기화 지연시켜 launch 경합을 재현한다.
3. arm controller active 전후에 명령 토픽 subscriber 수와 /joint_states의 비어 있지 않은 name 배열을 확인한다.
4. 동작 검증은 기본 모델, 중복 ROS_DOMAIN_ID/중첩 install/setup을 배제한 새 쉘에서 수행한다.

**판정: STATIC REVIEW COMPLETE / RUNTIME NOT VERIFIED / 시작 순서 검증이 필요.**

---
대응 실습: [LAB_5_2_GUIDE_KO.md](LAB_5_2_GUIDE_KO.md)
