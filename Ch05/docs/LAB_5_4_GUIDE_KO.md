# 5.4절 실습 가이드 — JointState 실측·오차 검증

## 코드 개정 반영 안내 (2026-10-21)
- 이제 listener는 Position 배열 길이·유한성을 검사하고, 누락 Velocity를 `N/A (not reported)`로 표시한다(0rad/s로 오인 금지).
- `--ros-args -p target_joint:=joint4 -p log_period_sec:=1.0`로 관절과 출력 주기를 변경해 볼 수 있다.
- 원고/옛 리뷰에 기재된 배열 인덱스 예외는 수정 이전 결함이다. 새 회귀 테스트: [SECTION_5_4_CHANGE_TEST_REPORT_KO.md](SECTION_5_4_CHANGE_TEST_REPORT_KO.md).


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
JointState 메시지의 name/position/velocity/effort 대응을 이해하고, 실측값·관절 명령·시각화 그래프를 같은 관절 기준으로 비교한다.

## 실습 1 — 토픽 구조와 발행률
5.2절 launch가 실행 중인지 확인한다.
~~~bash
ros2 interface show sensor_msgs/msg/JointState
ros2 topic echo /joint_states --once
ros2 topic hz /joint_states
~~~

한 메시지의 name 배열과 position/velocity/effort 배열 길이를 기록한다. name과 각 배열이 반드시 모두 같은 길이 또는 모두 존재한다고 가정하면 안 된다. effort는 빈 배열일 수 있다. timestamp가 증가하는지 확인한다.

## 실습 2 — joint2 추출 및 움직임
별도 터미널에서:
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run manipulation_basics joint_listener
~~~

또 다른 터미널:
~~~bash
ros2 run manipulation_basics simple_controller
~~~

joint2의 0↔0.5rad 목표에서 logger가 출력하는 라디안·도 단위를 비교한다(0.5 rad≈28.65°). 로그가 안 뜨면 JSB active, /joint_states 메시지 수신 및 target joint 존재 여부를 본다.

## 실습 3 — 시간 그래프
~~~bash
ros2 run rqt_plot rqt_plot
~~~

/joint_states 메시지를 echo하여 관절 이름 순서를 먼저 확인한다. 예를 들어 name[1]=joint2일 때에만 /joint_states/position[1]을 joint2로 해석할 수 있다. position[0]을 무조건 joint1이라고 읽지 않는다. 계단형 **명령 목표**와 실제 보간·센서 **실측 곡선**을 구분한다.

## 실습 4 — 결함을 설계 질문으로 전환
소스의 msg.position[index], msg.velocity[index]를 확인한다. msg.name에는 joint2가 있으나 position이 빈 비정상 데이터를 수신하면 IndexError가 발생할 수 있다. 개선안은 먼저 index < len(msg.position)를 검사하고 velocity는 index < len(msg.velocity)일 때만 사용하도록 하는 것이다. 수정된 노드에서는 해당 보호를 확인하고 새 단위 테스트로 회귀 검증한다.

## 체크포인트
정상 움직임 2주기 동안 실제 각도 변화, 주기, /joint_states 토픽 주파수를 기록한다. PID 제어/추종 성능이 검증됐다고 과장하지 않는다.

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.4절 대응 리뷰: [SECTION_5_4_REPORT_KO.md](SECTION_5_4_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
