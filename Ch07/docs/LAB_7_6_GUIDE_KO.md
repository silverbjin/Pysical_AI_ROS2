# LAB_7_6_GUIDE_KO — 7.6절 그리퍼 제어와 파라미터 튜닝

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 제어 노드 존재, 시뮬레이터 실행·물리 파지 미검증**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 제어기 계약부터 확인
~~~bash
# Ubuntu 24.04 / ROS 2 Jazzy 전제. Ch07 단독 overlay에서 실행
source /opt/ros/jazzy/setup.bash
cd Pysical_AI_ROS2/Ch07/ros2_ws
echo "$ROS_DISTRO"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | head -20
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
ros2 pkg prefix vision_basics
~~~
~~~bash
grep -n 'joint_finger\|<limit' src/vision_basics/urdf/my_robot.urdf.xacro
grep -n 'gz_ros2_control\|ros2_control' src/vision_basics/urdf/my_robot.urdf.xacro
grep -n 'gripper_group_controller' src/vision_basics/config/ros2_controllers.yaml
grep -n 'gripper_group_controller' src/my_robot_moveit_config/config/ros2_controllers.yaml
ros2 pkg executables vision_basics
~~~

**중요:** 원고에는 gripper_left_finger_link라고 적혀 있으나 실제 URDF의 링크는 finger1/finger2이다. 수정 전 그 이름에 대한 Gazebo 태그는 모델에 반영되지 않을 수 있다.

## 시뮬레이터 제어기 활성화 후에만 실행
~~~bash
ros2 control list_controllers
ros2 action list -t | grep gripper
ros2 topic echo --once /joint_states
# node entry point 등록 후에만!
ros2 run vision_basics gripper_controller
~~~

관찰: gripper_group_controller가 active, 액션 타입 FollowJointTrajectory, joint_finger1/2가 함께 이동, prismatic 위치의 단위 m. 원본 demo는 비동기 호출 뒤 spin 전 sleep하므로 바로 실행하기보다 먼저 안전하게 Action 완료대기 방식으로 수정한다.

## 마찰·파지 실험 설계
표준 조건의 (1) 손가락 간격, (2) 접촉 후 물체 자세, (3) +10cm 리프트 중 미끄러짐, (4) 3회 반복 성공 횟수를 기록한다. 변경 변수는 마찰·접촉 강성·감쇠 중 하나로 제한한다. 큰 계수를 미리 성공값으로 간주하지 않는다.

**완료 기준:** open/close 액션 상태 성공, 관절 이동 확인, 실제 물체 들어올리기 성공, 3회 반복/실패 조건 및 접촉 설정 기록. ROS 2 제어기 및 물리 파지 실측은 미수행이다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_6_REPORT_KO.md](SECTION_7_6_REPORT_KO.md).
