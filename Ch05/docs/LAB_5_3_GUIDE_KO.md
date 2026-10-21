# 5.3절 실습 가이드 — Python JointTrajectory 발행

## 코드 개정 반영 안내 (2026-10-21)
- simple_controller는 controller 구독자가 없을 때 목표 발행/토글을 보류한다.
- 한 점의 위치뿐 아니라 **끝점 속도 0rad/s**도 전달해 Jazzy JTC cubic 보간을 사용하도록 변경됐다. `ros2 topic echo`의 `velocities: [0,0,0,0]`도 확인한다.
- `validate_goal()`에서 4축 목표 개수·유한성·URDF 관절 범위를 검사한다. 보고서: [SECTION_5_3_CHANGE_TEST_REPORT_KO.md](SECTION_5_3_CHANGE_TEST_REPORT_KO.md).


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
한 점짜리 JointTrajectory 메시지를 직접 관찰하고, '명령 전송'과 '측정 상태가 목표에 도달'을 구별한다.

## 실습 1 — 선행 조건 확인
5.2절 실행 상태에서 새 터미널을 열고 공통 setup을 source한다.
~~~bash
cd ~/Pysical_AI_ROS2/Ch05/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 control list_controllers
ros2 topic info /arm_controller/joint_trajectory -v
~~~

arm_controller가 active이고 subscriber가 있을 때만 계속한다.

## 실습 2 — 정답 파일과 실행 명령 사용
터미널 C:
~~~bash
ros2 run manipulation_basics simple_controller
~~~

원고에 쓰인 simple_trajectory_publisher.py는 현재 저장소에 없으며 올바른 소스는 manipulation_basics/simple_joint_controller.py다. source install/setup.ros2, run manipulation_basics ...도 잘못된 명령이다.

터미널 D:
~~~bash
ros2 topic echo /arm_controller/joint_trajectory --once
ros2 topic echo /joint_states --once
~~~

예상 명령: joint_names가 joint1~joint4, 첫 굽힘 목표 [0.0,0.5,0.5,1.0] rad, home [0,0,0,0] rad, point.time_from_start=1초. 노드는 매 2초마다 목표를 교대한다. echo --once는 어느 시점의 단일 메시지를 잡느냐에 따라 home 또는 bending일 수 있다.

## 실습 3 — 목표와 실제 오차 해설
명령의 각 관절 값을 표로 적고, /joint_states에서 같은 이름의 실제 position을 찾아 e_i = command_i - measured_i(rad)를 구한다. 배열의 같은 **인덱스**가 아니라 관절 **이름** 기준으로 매핑한다. 명령 직후 과도 상태와 1초 뒤 정상 상태를 구분한다. /joint_states 타임스탬프와 토픽 수신 시점을 남긴다.

## 실패 진단
- 로그는 Goal을 출력하지만 팔이 안 움직임: arm_controller inactive, 잘못된 topic, subscriber 수 0, ROS_DOMAIN_ID 충돌 가능.
- 비정상 도약: 중복 명령 노드, 물리 파라미터, 초깃값, joint limit/velocity 확인.
- 별도 wave_hello를 함께 실행하지 않는다. 동일 topic에 두 publisher가 경쟁한다.

## 실습 확장
목표 지속시간을 1초와 3초로 바꿨을 때 실제 궤적, 최대 관절속도, 목표 도달 시간을 기록하되 안전한 시뮬레이터에서만 실시한다.

## 제출할 증거와 학습 확인
- 실행에 사용한 ROS/Gazebo 버전, 체크아웃 커밋, 빌드 성공/실패 및 종료코드, 사용 명령을 기록한다.
- 예상 출력은 체크 조건이지 본 문서 작성자가 실제 관측했다는 뜻이 아니다. 오류 시 로그를 그대로 남기고 우회·추측으로 PASS 처리하지 않는다.
- 5.3절 대응 리뷰: [SECTION_5_3_REPORT_KO.md](SECTION_5_3_REPORT_KO.md). 원고/구현 차이와 제한을 함께 읽는다.
