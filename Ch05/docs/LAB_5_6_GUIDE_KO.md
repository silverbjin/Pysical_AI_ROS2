# 5.6절 실습 가이드 — 사인파 Hello Robot 검증 프로젝트

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
서로 다른 각주파수로 만든 4관절 궤적의 단위와 시뮬레이션 시간을 이해하고, 목표 신호와 실제 상태의 차이 및 빠른 반복 발행의 위험을 관찰한다.

## 수학 계약 및 사전 위험 확인
- joint1 = 0.3 sin(1.0t) rad: 각주파수 ω=1.0 rad/s, 주기≈6.28초, 최대 속도≈0.3 rad/s.
- joint4 = 0.5 sin(4.0t) rad: ω=4.0 rad/s, 주기≈1.57초, 최대 속도=2.0 rad/s.
- 고정 자세 joint2=-0.5rad, joint3=0.8rad. 현재 노드는 **첫 명령에서 이 자세로 0.02초 안에 도달하도록 요구**할 수 있다. URDF joint4 velocity limit=2.0rad/s이므로 물리 안정성을 미리 보장할 수 없다.
- 무부하 가상환경에서만 관찰하고, 불안정하면 즉시 Ctrl+C로 중단한다. 시작 구간의 급격한 목표 변경을 제거하는 수정 전에는 실제 하드웨어에 사용하지 않는다.

## 실습 1 — 시계·컨트롤러 준비
5.2절 시뮬레이터 실행 후:
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 topic echo /clock --once
ros2 control list_controllers
ros2 topic info /arm_controller/joint_trajectory -v
~~~

이전에 실행한 simple_controller는 반드시 종료한다. clock이 들어오고 arm_controller가 active인 상태에서만 wave_hello를 켠다.

## 실습 2 — 올바른 시간 옵션으로 노드 실행
~~~bash
ros2 run manipulation_basics wave_hello --ros-args -p use_sim_time:=true
~~~

다른 터미널에서:
~~~bash
ros2 param get /wave_hello_node use_sim_time
ros2 topic echo /arm_controller/joint_trajectory --once
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
~~~

실제 저장소는 get_clock()을 사용하지만 use_sim_time을 내부에서 켜지 않는다. 따라서 위 CLI 파라미터가 중요하다. ROS 시간 0 근처의 초기화, 시뮬레이션 pause/재시작, 시계 점프에서도 재현성이 확보되는지 추가 확인해야 한다.

## 실습 3 — 그래프로 원리 검증
~~~bash
ros2 run rqt_plot rqt_plot
~~~

먼저 /joint_states의 name 배열에서 joint1과 joint4의 실제 인덱스를 찾는다. 두 관절 position을 각각 추가하고 적어도 13초 동안 관찰한다. 주기 약 6.28초와 1.57초가 나타나는지 확인한다. 원하는 목표 진폭과 실제 측정 진폭이 일치하는지는 별도의 오차 문제다. 현재 코드는 20ms마다 단일 점 trajectory를 교체하므로 메시지 수신률·추종·지터를 측정하지 않고 '완벽한 사인 곡선'이라 판정하지 않는다.

## 실습 4 — 개선 과제(코드 수정 후 별도 검증)
1. 안전한 시작 포즈로 2~3초 이동한 후에 파형을 시작한다.
2. joint4의 진폭/각주파수를 낮춰 최대 속도에 여유를 둔다.
3. 타임스탬프 기반 multi-point trajectory와 현재 20ms 재전송 방식을 비교한다.
4. 각 관절 추종 오차, 발행/수신 주기, 종료 후 마지막 위치 유지 여부를 기록한다.

## 오류 진단
- 두 노드가 같은 토픽 발행: simple_controller를 중지하고 재시도.
- 그래프가 튀거나 멈춤: /clock의 연속성, sim_time, controller 상태, 목표가 너무 급한지 확인.
- RViz 동작만 확인됨: Gazebo 물리 joint_states 및 실제 오차까지 검증해야 성공 판정 가능.

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.6절 대응 리뷰: [SECTION_5_6_REPORT_KO.md](SECTION_5_6_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
