# LAB 3.6 — ros_gz_bridge에서 시계·관절 토픽 연결

## 핵심 구조
`Gazebo` → `gz.msgs.Model` → `ros_gz_bridge` → ROS `sensor_msgs/msg/JointState` → `robot_state_publisher` → `/tf`. 그리고 ROS `std_msgs/msg/Float64` → `ros_gz_bridge` → Gazebo `gz.msgs.Double` → 위치 제어 플러그인. **시뮬레이션 시계는 Gazebo → ROS 한 방향**이다.

## 1. 설치·빌드
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-ros-gz
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
```

## 2. 실제 Gazebo 토픽 확인
```bash
ros2 launch my_robot_description spawn_robot.launch.py
# 두 번째 터미널, 같은 ROS 및 워크스페이스 source 후:
gz topic -l
ros2 topic list
ros2 topic echo /clock --once
```
월드 이름은 `my_first_world`, 모델 이름은 `my_robot`. 실제 Gazebo `joint_state` 토픽은 해당 엔티티가 스폰되고 플러그인이 로드된 **후**에 생성된다. 오타가 나면 YAML에서 `gz_topic_name`을 수정해야 한다.

## 3. 명령 방향 실습
```bash
ros2 topic pub --once /joint2/cmd_pos std_msgs/msg/Float64 '{data: 0.5}'
ros2 topic echo /joint_states --once
```
3.8의 위치 제어 플러그인과 joint state publisher가 실행된 통합 환경에서만 실제 반응을 확인할 수 있다. `ros2 topic pub` 정상 종료만으로 제어 성공을 주장하지 않는다. `cmd_vel`은 여기서 **브리지 구성 예시**일 뿐 2축 팔 움직임을 유발하지 않는다.

## 4. CLI 기호 비교
```bash
ros2 run ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
```
`[`는 Gazebo→ROS, `]`는 ROS→Gazebo, `@`는 양방향. 이 별도 실습을 할 때 기존 통합 브리지와 **동시 실행하지 말 것**(중복 퍼블리셔 예방).

## 5. 오류를 좁히는 순서
1. Gazebo 내부 토픽 존재(`gz topic -l`)
2. `ros2 node list`에서 bridge 확인
3. `ros2 topic info /joint_states -v`에서 ROS QoS/타입 확인
4. RSP `use_sim_time:=true` 확인 및 `/tf` 중복 publisher 검사
5. PID 플러그인·시뮬레이션 일시정지 여부 확인

Evidence: YAML diff, `gz topic -l`, `ros2 topic echo /clock --once`, 명령 전후 관절각 로그, 오류 있으면 log. [리뷰](SECTION_3_6_REPORT_KO.md).
