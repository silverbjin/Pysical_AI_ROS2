# 5.1절 실습 가이드 — 기초 제어 패키지 준비와 정적 매핑

## 코드 개정 반영 안내 (2026-10-21)
- 현재 이 브랜치에서 gripper_controller 미사용 선언은 **제거됨**. 파트 5.1의 검사에서 그리퍼가 나타나지 않아야 정상이다.
- `open_loop_control`은 deprecated 설정이므로 제거됨; 사용자 메시지 발행의 개루프 성격과 JTC 내부 상태 처리를 구분한다.
- package.xml의 ROS/Gazebo 실행 의존성과 setup.py 0.0.1 버전이 보완됨. 검증 보고서: [SECTION_5_1_CHANGE_TEST_REPORT_KO.md](SECTION_5_1_CHANGE_TEST_REPORT_KO.md).


## 공통 환경과 주의사항
- 전제: Ubuntu 24.04(WSL2 가능), ROS 2 Jazzy, Gazebo Harmonic 및 ros2_control/gz_ros2_control/ros_gz_* 관련 패키지 설치. 실제 설치/동작은 본 문서 작업 환경에서 검증하지 못했다.
- 저장소 루트가 홈 폴더에 있지 않다면 아래 경로를 본인의 체크아웃 경로로 바꾼다.
- 다른 장의 install 경로가 AMENT_PREFIX_PATH에 겹치면 엉뚱한 URDF가 선택될 수 있다. 새 터미널에서 /opt/ros/jazzy/setup.bash만 먼저 source한다.
- 로봇이 예기치 않게 움직이거나 controller inactive면 명령 노드를 중지하고 상태를 점검한다. 본 예제는 실제 로봇에 바로 적용하지 않는다.

~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select manipulation_basics
source install/setup.bash
ros2 pkg prefix manipulation_basics
ros2 pkg executables manipulation_basics
~~~

빌드 또는 패키지 조회가 실패하면 이후 단계로 넘어가지 않는다. 특히 xacro, ros_gz_sim, ros_gz_bridge, gz_ros2_control, controller_manager, joint_trajectory_controller, robot_state_publisher, rviz2가 현재 환경에서 사용 가능한지 점검한다.

## 학습 목표
개루프 상위 명령 발행과 하위 제어기의 차이를 설명하고, 패키지 구조·제어기 YAML·URDF 관절 이름을 대조한다. 아직 Gazebo 동작 성공을 목표로 삼지 않는다.

## 실습 1 — 파일과 엔트리포인트 확인
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws/src/manipulation_basics
find . -maxdepth 3 -type f | sort
grep -n 'console_scripts\|simple_controller\|joint_listener\|wave_hello' setup.py
grep -n 'arm_controller\|joint1\|joint4\|gripper_controller' config/ros2_controllers.yaml
grep -n 'joint name=' urdf/robot.ros2_control.xacro
~~~

예상: simple_joint_controller.py, joint_state_listener.py, wave_hello_node.py가 보이고 simple_controller → manipulation_basics.simple_joint_controller:main로 연결된다. 원고의 simple_trajectory_publisher.py는 실제 파일이 아니다.

## 실습 2 — 제어기 인터페이스 계약 읽기
- YAML의 arm_controller.joints 순서를 적고 URDF의 joint1~joint4와 모두 동일한지 확인한다.
- command_interfaces에 position, state_interfaces에 position/velocity가 있는지 찾는다.
- joint_trajectory_controller는 상위 명령의 시간 기반 궤적을 처리한다. 원고의 '개루프'는 피드백을 읽지 않는 **사용자 publisher**의 형태를 가리킨다. 전체 스택을 피드백 없는 시스템으로 오인하지 않는다.
- 개정 YAML에는 gripper_controller 설정이 없음을 확인한다(현재 로봇에 gripper_joint가 없음).

## 실습 3 — 의존성·빌드 진단
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
ros2 pkg prefix ros_gz_sim
ros2 pkg prefix ros_gz_bridge
ros2 pkg prefix controller_manager
ros2 pkg prefix xacro
ros2 pkg prefix robot_state_publisher
ros2 pkg prefix rviz2
colcon test --packages-select manipulation_basics
colcon test-result --verbose
~~~

환경에 따라 일부 패키지가 없을 수 있다. package.xml에 실행 의존성이 빠져 있으므로 설치 여부를 직접 확인해야 한다. 테스트 스캐폴드의 lint PASS만으로 시뮬레이터 구동 성공을 주장하면 안 된다.

## 학습 질문
1. position 명령 인터페이스와 position 상태 인터페이스는 정보 방향이 어떻게 다른가?
2. 왜 이름이 일치해도 /joint_states 확인이 필요한가?
3. 소스 이름이 원고와 다를 때 무엇을 기준으로 정확한 실행 명령을 확정하는가?

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.1절 대응 리뷰: [SECTION_5_1_REPORT_KO.md](SECTION_5_1_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
