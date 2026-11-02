# 6.3절 실습 가이드 — Ch06 실제 로봇으로 MoveIt 구성 생성

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.3절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 학습 목표
URDF(Xacro) → SRDF(체인, EE, 자세, ACM) → MoveIt 설정 패키지의 관계를 이해하고 기존 설정과 생성 결과를 차분(diff)으로 비교한다.

## 준비와 무결성 검사
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 run xacro xacro src/my_robot_description/urdf/my_robot.urdf.xacro > /tmp/ch06_robot.urdf
check_urdf /tmp/ch06_robot.urdf
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```
기존 `my_robot_moveit_config` 패키지를 **덮어쓰지 않는다**. Setup Assistant 생성물은 새 실습 디렉터리(예: `/tmp/ch06_moveit_generated`)에 보관한다.

## GUI 설정 순서
1. Create New Configuration에서 `/tmp/ch06_robot.urdf` 로드; 3D 모델·충돌 형상 확인.
2. Self-Collisions 생성 후 과도한 Never 제외가 없는지 시각 확인.
3. Virtual Joint는 URDF 루트를 검사한 뒤 단일 기준(보통 world→base_link)을 정의한다. **URDF에 이미 world 고정조인트가 있다면 중복 설정하지 않는다.**
4. Planning Group `arm_group`: `base_link → link_wrist` 체인, 실 구동 관절 `joint1, joint2, joint3, joint4, joint_wrist` 확인. KDL 사용. 5축 로봇에 6D IK를 무조건 요구하지 않는다.
5. `gripper_group`: `joint_finger1`, `joint_finger2`를 추가. End Effector `hand_ee`, parent `link_wrist`, parent group `arm_group`.
6. Named Pose `home`/ `ready`를 SRDF에 저장(기존 저장소에는 `ready`의 `joint3=1.5708`rad 정의).
7. Controllers 단계에서 5개의 arm 조인트와 FollowJointTrajectory, 그리퍼의 **실제 액션 타입/단일·복수 관절 요구**를 확인하고 기존 ROS 2 Control과 비교.
8. 저장 패키지의 `config/my_robot.srdf`, `kinematics.yaml`, `moveit_controllers.yaml`, `ros2_controllers.yaml`를 기존 파일과 diff.

## 실행 전 게이트
```bash
P=$(ros2 pkg prefix my_robot_moveit_config)
find "$P/share/my_robot_moveit_config" -maxdepth 3 -type f | sort
ros2 launch my_robot_moveit_config demo.launch.py
```
위 demo는 RViz 가상 모델/컨트롤러가 정상일 때에만 Plan & Execute 확인이 가능하다. 바로 실행되지 않을 경우 `Rviz_Demo.launch.py`와 컨트롤러의 차이를 조사한다. `demo.launch.py`는 Gazebo 물리 시뮬레이터가 아니다.

## 제출 증거
`check_urdf` 결과, 새로 생성한 SRDF(arm/gripper/EE), 모델 루트·TF 확인 결과, 플래너 상태, 충돌 설정 비교표. [리뷰](SECTION_6_3_REPORT_KO.md).
