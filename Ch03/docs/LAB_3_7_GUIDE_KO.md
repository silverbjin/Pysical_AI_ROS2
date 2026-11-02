# LAB 3.7 — 한 번의 Launch로 Gazebo에 로봇 스폰

## 학습 목표
RSP가 모델 XML을 `/robot_description`으로 발행하고 `ros_gz_sim create`가 이를 읽어 Gazebo에 `my_robot` 엔티티를 만드는 실행 구조를 이해한다. `-file`/ `-topic` 방식을 모두 체험한다.

## 1. 사전 점검
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 pkg prefix my_robot_description
xacro src/my_robot_description/urdf/two_dof_arm.urdf.xacro > /tmp/ch03_spawn.urdf
check_urdf /tmp/ch03_spawn.urdf
```

## 2. 수동 스폰(별도 시험)
터미널 A:
```bash
gz sim -v 4 -r src/my_robot_description/worlds/my_world.sdf
```
터미널 B(ROS source):
```bash
ros2 run ros_gz_sim create -world my_first_world -name my_arm_test -file /tmp/ch03_spawn.urdf -z 0.1
```
모델명이 `my_arm_test`인 시험과 통합 실행의 `my_robot` 이름을 **동시에 섞지 않는다**. 로그에서 실제 entity 생성 성공을 확인하고 서버를 종료한다.

## 3. 통합 스폰
```bash
ros2 launch my_robot_description spawn_robot.launch.py
```
런치 내부에서 Gazebo world, RSP, create, 브리지를 시작한다. Gazebo의 서버·GUI·`create` 응답은 별개이므로 하나가 살아있다고 전체 성공은 아니다.

## 4. 확인
새 터미널에서 source 후:
```bash
ros2 node list
ros2 topic echo /robot_description --once
ros2 topic echo /clock --once
ros2 param get /robot_state_publisher use_sim_time
gz topic -l | grep -E 'clock|joint_state|cmd_pos'
```
**예상**: RSP 존재, XML 발행, Clock 증분; joint state 및 cmd_pos 확인은 3.8 플러그인에 의존한다.

## 5. 고장 주입·복구
`-name`을 기존 엔티티 이름과 동일하게 수동 스폰하면 중복 이름 에러가 나야 한다. 별도 월드 이름을 쓰면 브리지의 `/world/my_first_world/model/my_robot/joint_state` 경로도 바뀐다. 변경은 실습용 임시 파일에서만 수행.

## 합격 조건
Xacro/check_urdf, colcon, Gazebo create 응답, `/robot_description`, `/clock`, 모델 스크린샷 및 종료 로그 수집. 물리적으로 베이스가 고정인지 따로 확인한다. [리뷰](SECTION_3_7_REPORT_KO.md).
