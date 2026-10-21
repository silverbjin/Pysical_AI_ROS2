# 5.5절 실습 가이드 — Gazebo와 RViz 상태 미러링

## 코드 개정 반영 안내 (2026-10-21)
- RViz RobotModel의 `/robot_description` 구독 Durability를 `Transient Local`로 변경해 뒤늦은 RViz 실행에서도 기존 모델 설명을 받을 수 있도록 설정했다.
- `manipulation.rviz`의 Fixed Frame 기본값을 **world**로 변경했다. 현재 URDF의 world→base_link 고정 연결을 기준으로 해석한다.
- 별도 RViz만 확인하려면 **이미 로봇 description/TF를 발행하는 별도 실행 환경**에서 `ros2 launch manipulation_basics rviz_only.launch.py`. 기존 통합 launch와 동시에 실행하면 RViz가 중복된다.
- 보고서: [SECTION_5_5_CHANGE_TEST_REPORT_KO.md](SECTION_5_5_CHANGE_TEST_REPORT_KO.md).


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
Gazebo의 물리 모델과 RViz RobotModel/TF 표현을 구분하고, /robot_description + /joint_states → robot_state_publisher → TF의 데이터 경로를 확인한다.

## 실습 1 — 설치와 RViz 설정 검사
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 pkg prefix manipulation_basics
ls install/manipulation_basics/share/manipulation_basics/rviz/manipulation.rviz
~~~

실제 설정 위치는 **패키지 루트**의 rviz/manipulation.rviz다. 원고에 적힌 manipulation_basics/manipulation_basics/rviz는 setup.py glob 설치 위치와 다르다.

## 실습 2 — GUI와 상태 확인
터미널 A:
~~~bash
ros2 launch manipulation_basics manipulation_system.launch.py
~~~

예상: Gazebo와 RViz가 실행되고 RViz Fixed Frame=base_link, RobotModel Description Topic=/robot_description, TF display가 활성화된다. GUI가 뜨더라도 아래 명령으로 동작 여부를 점검한다.

터미널 B:
~~~bash
ros2 topic echo /joint_states --once
ros2 topic echo /robot_description --qos-durability transient_local --once
ros2 param get /robot_state_publisher use_sim_time
ros2 param get /rviz2 use_sim_time
ros2 run tf2_ros tf2_echo base_link link4
~~~

TF가 조회되지 않으면 robot_state_publisher, joint_state_broadcaster, 메시지 stamp, /clock 경로와 중복 TF publisher 여부를 차례로 확인한다.

## 실습 3 — 같은 움직임 비교
터미널 C에서 ros2 run manipulation_basics simple_controller를 실행한다. Gazebo와 RViz에 표시되는 관절 움직임의 **방향·순서·상대 자세**를 비교한다. base_link가 고정된 이 모델은 외부 충돌로 베이스가 튕기는 실험이 아니며, RViz 자체가 Gazebo의 충돌/접촉을 그대로 복제하는 것도 아니다.

## 문제 해결
- RobotModel Error: /robot_description, 모델 파싱, description topic 확인.
- TF Error: Fixed Frame과 link 이름, /joint_states 갱신, use_sim_time 확인.
- 경로 오류: 저장소의 패키지 루트 rviz/가 설치 대상. 소스 변경 후 colcon build 재실행.
- WSLg 창이 뜨지 않으면 그래픽 세션 지원 확인. headless 환경에서는 토픽/TF까지 검증하고 GUI는 NOT VERIFIED로 남긴다.

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.5절 대응 리뷰: [SECTION_5_5_REPORT_KO.md](SECTION_5_5_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
