# LAB 2.3 — Topic 통신: 속도 발행과 위치 구독

## 학습 목표
`Twist` 발행 → turtlesim 구독 → `Pose` 발행 → 우리 subscriber 수신의 왕복 **데이터 흐름**을 확인한다. 여기서 토픽 각각은 단방향이며 전체 응용이 순환 구조임을 구분한다.

## 사전 점검
Ubuntu 24.04 ROS 2 Jazzy. 실습 기준은 `Ch02/ros2_ws` (원고의 `~/ros2_ws`와 혼동 금지). 2.3 브랜치의 의존성 변경이 적용되어 있어야 한다.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_system
```

## 3개 터미널 실습
모든 터미널에서 `source /opt/ros/jazzy/setup.bash` → `source ~/Pysical_AI_ROS2/Ch02/ros2_ws/install/setup.bash` 순으로 source.

**A**
```bash
ros2 run turtlesim turtlesim_node
```

**B**
```bash
ros2 run my_robot_system turtle_pose_sub
```
구독자가 약 60Hz 수준으로 좌표를 로그로 출력할 수 있다. 초당 실제 로그 수는 부하에 따라 달라진다. 움직이지 않을 때도 Pose가 갱신될 수 있다.

**C**
```bash
ros2 run my_robot_system turtle_cmd_pub
```
거북이가 원을 그리며 움직이며 B의 X/Y/Theta가 달라진다. 경계에 닿으면 궤적이 달라질 수 있다.

## 4번째 진단 터미널
```bash
ros2 node list
ros2 topic list -t
ros2 topic info -v /turtle1/cmd_vel
ros2 topic hz /turtle1/cmd_vel
ros2 topic echo /turtle1/pose --once
ros2 interface show geometry_msgs/msg/Twist
rqt_graph
```
`hz`는 몇 초 관찰 후 Ctrl+C. 명령 발행 주기는 0.5초 → 이론상 약 **2Hz**. 그래프가 간략히 보이면 GUI에서 Nodes/Topics 표시 필터를 확인한다.

## 탐구·고장 주입
1. C를 정지한다. Pose subscriber B가 계속 수신하더라도 좌표가 멈추는지 확인.
2. C의 토픽명을 `/wrong/cmd_vel`로 일시 변경하면 토픽이 보이더라도 거북이는 움직이지 않음을 확인(`ros2 topic info -v`).
3. 원복 후 다시 빌드·테스트하고 `git diff`를 확인한다.

## 평가 기준
발행 토픽, 구독 토픽, 메시지 타입, 발행주기, ROS graph 경로를 노트로 정리. 실제 모터에 속도 명령을 복제하는 실습이 아니며, 안전 watchdog은 별개다. 정리는 C→B→A 순서로 Ctrl+C. [리뷰 보고서](SECTION_2_3_REPORT_KO.md).