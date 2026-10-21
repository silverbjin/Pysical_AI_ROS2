# 5.2절 실습 가이드 — Gazebo 소환과 컨트롤러 활성화

## 코드 개정 반영 안내 (2026-10-21)
- 이제 실행 순서는 **Gazebo create 정상 종료 → JSB spawner 정상 종료 → arm spawner**이다. 과거 '2초 대기' 설명은 수정 전 코드에 한정된다.
- 실패 종료코드면 후속 스포너를 시작하지 않고 launch를 종료한다. 여전히 실제 active 상태는 `ros2 control list_controllers`로 직접 확인한다.
- 수정 보고서: [SECTION_5_2_CHANGE_TEST_REPORT_KO.md](SECTION_5_2_CHANGE_TEST_REPORT_KO.md).


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
Xacro → robot_description → Gazebo create → controller_manager/spawner → /joint_states와 /clock 흐름을 확인하고, 시동 시점 경쟁 문제를 재현·분리한다.

## 실습 1 — URDF 변환과 구조 확인
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
xacro src/manipulation_basics/urdf/robot.urdf.xacro > /tmp/ch05_robot.urdf
grep -n 'ros2_control\|gz_ros2_control\|joint1\|joint4' /tmp/ch05_robot.urdf
~~~

기대: xacro 변환 종료코드 0, gz_ros2_control/GazeboSimSystem 및 4개 관절 정의. 패키지 탐색 실패 시 common setup을 재확인한다.

## 실습 2 — Gazebo와 제어기 실행
터미널 A:
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch manipulation_basics manipulation_system.launch.py
~~~

터미널 B(동일 두 setup source):
~~~bash
ros2 control list_controllers
ros2 control list_hardware_interfaces
ros2 topic list
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
ros2 topic info /arm_controller/joint_trajectory -v
~~~

성공 판정은 **joint_state_broadcaster와 arm_controller 둘 다 active**, /clock 수신, /joint_states의 name에 관절 4개 포함, /arm_controller/joint_trajectory subscriber 존재다. Gazebo 화면만 떴거나 스포너가 로그를 출력했다는 사실만으로 성공이 아니다.

## 실습 3 — 왜 2초 대기만으로는 부족한가?
launch/manipulation_system.launch.py에서 OnProcessExit(spawn_entity) → joint_state_broadcaster spawner 실행, OnProcessStart(JSB spawner) → TimerAction(2초) → arm spawner 순서를 찾아 그린다. 여기서 **프로세스 시작과 제어기 active는 다르다**. launch 로그의 create 종료코드, JSB spawner의 정상 종료와 controller state를 분리 기록한다.

재실행 3회 이상에서 두 제어기 상태 및 /clock 수신 시간을 기록한다. 실패 시 /controller_manager 노드/서비스, Gazebo의 플러그인 로딩 오류, spawn 실패, 다른 overlay로 인한 모델 충돌 순으로 확인한다.

## 문제 해결
- xacro command not found: xacro 설치와 ROS overlay.
- Package not found: 새 터미널에서 source /opt/ros/jazzy/setup.bash → source install/setup.bash.
- controller_manager unavailable: gz_ros2_control 플러그인, YAML 로드/이름 일치, Gazebo 모델 생성 확인.
- RViz만 보이거나 Gazebo가 pause: /clock 변화와 Gazebo 실행 상태 확인.

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.2절 대응 리뷰: [SECTION_5_2_REPORT_KO.md](SECTION_5_2_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
