# 4.6절 실습 가이드: Gazebo 관절 상태를 RViz와 동기화

**실습 목적:** Gazebo 내부 관절 상태를 ROS의 `/joint_states`로 전달한 다음 RSP가 계산한 TF를 RViz로 확인한다. **전체 몸체 pose 동기화는 별도의 확장 과제**다.

## 1. 환경 및 현재 소스 위치

- Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + `ros_gz_sim` / `ros_gz_bridge` / `robot_state_publisher` / RViz2.
- 실행 패키지는 **Ch04가 아닌 Ch03**: `Ch03/ros2_ws/src/my_robot_description`.
- 사용하는 모델: `two_dof_arm.urdf.xacro`, 실제 Gazebo world: `empty`.
- 같은 시간에 `joint_state_publisher_gui`를 실행하지 않는다(관절 상태 발행자 중복 방지).

```bash
source /opt/ros/jazzy/setup.bash
ros2 pkg prefix ros_gz_sim
ros2 pkg prefix ros_gz_bridge
ros2 pkg prefix robot_state_publisher
ros2 pkg prefix rviz2
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select my_robot_description --symlink-install
source install/setup.bash
```

## 2. 통합 실행 (터미널 A)

```bash
ros2 launch my_robot_description sim_sync.launch.py
```

Gazebo가 시작되고 `my_robot`이 spawn되었는지 **실제 로그**로 확인한다. `create` 노드 실패 시 RSP의 `/robot_description` 수신과 spawn 타이밍을 조사한다. `display.launch.py`는 GUI용 별도 launch이므로 중복 실행하지 않는다.

## 3. Gazebo/ROS 관절·시간 확인 (터미널 B)

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch03/ros2_ws/install/setup.bash
gz topic -l | grep -E 'joint_state|clock'
gz topic -i -t /world/empty/model/my_robot/joint_state
ros2 topic list -t
ros2 topic echo --once /clock
ros2 topic echo --once /joint_states
ros2 topic info /joint_states -v
ros2 param get /robot_state_publisher use_sim_time
```

**예상:** `/world/empty/model/my_robot/joint_state`는 Gazebo의 `gz.msgs.Model`; ROS `/joint_states`는 `sensor_msgs/msg/JointState`. 실제 Gazebo 토픽이 없으면 `gz topic -l`의 world/model 이름을 확인하고 launch bridge 설정을 일치시킨다. 별도 `ros_gz_bridge.yaml`의 `my_first_world`를 `empty`와 혼용하지 않는다.

## 4. RSP와 RViz 확인 (터미널 C)

```bash
ros2 run tf2_ros tf2_echo base_link link2
ros2 run tf2_tools view_frames
```

RViz의 Fixed Frame은 `base_link`; Add → TF + RobotModel을 확인한다. RobotModel 형상이 없으면 Description Source/Topic `/robot_description`과 QoS 및 실제 TF 트리를 확인한다. `view_frames`에서 `base_link→link1→link2`가 나타나는지 점검한다.

## 5. 관절 동기화 테스트와 한계

관절을 실제로 움직이는 데는 4.7절의 제어 노드가 필요하다. `/joint2/cmd_pos` 브리지를 확인한 후 다음 절의 명령을 실행하고 `/joint_states` 및 `tf2_echo base_link link2`가 변경되는지 비교한다. 둘 다 변경되면 **관절 동기화**는 작동한다.

**주의:** Gazebo 창에서 힘을 가해 로봇의 base가 쓰러져도 `/joint_states`만으로 `world→base_link`가 자동 발행되지는 않는다. 그러므로 RViz 전체 자세가 바뀌지 않았더라도 관절 파이프라인 실패라고 단정하지 않고, **세계 좌표 포즈 미구현**으로 기록한다.

## 6. 실패 분석과 제출물

| 증상 | 우선 진단 |
|---|---|
| /clock 없음 | Gazebo world 실행·bridge 방향과 토픽 |
| Gazebo joint_state 없음 | 모델 spawn·JointStatePublisher 플러그인·world 명칭 |
| ROS /joint_states 없음 | Gazebo 토픽과 bridge의 실제 이름/형식·remap |
| /joint_states 존재, RViz 정지 | RSP 로그·/tf·TF frame 연결·use_sim_time |
| Gazebo base는 이동, RViz base 고정 | 월드 기준 base pose TF 미구현 |

제출 자료: Gazebo·bridge 실행 로그, `gz topic -l`, `ros2 topic list -t`, `/clock`, `/joint_states`, `view_frames`, RViz 캡처. **합격은 관절 동기화까지만** 판정하고 전체 몸체 pose는 개선 과제로 남긴다.

[4.6절 리뷰 보고서](SECTION_4_6_REPORT_KO.md)
