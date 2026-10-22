# LAB 3.8 — PID 위치제어로 Gazebo 2축 관절 움직이기

## 목표
`JointStatePublisher`(측정) + `JointPositionController`(명령) + `ros_gz_bridge`(메시지 변환)를 연결한다. 3.7 스폰, 3.6 브리지, 3.3 Xacro 관성 수정과 함께 검증한다.

## 1. 준비 및 실행
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description spawn_robot.launch.py
```
통합 실습에서 `joint_state_publisher_gui`를 동시에 켜지 않는다. Gazebo가 실제 joint 상태를 발행해야 한다.

## 2. 플러그인 토픽 점검
별도 터미널에서 ROS 환경 source 후:
```bash
gz topic -l | grep -E 'joint_state|cmd_pos'
ros2 topic list | grep -E 'joint_states|joint[12]/cmd_pos'
ros2 topic echo /joint_states --once
```
Gazebo 쪽 명령 토픽은 `/model/my_robot/joint1/cmd_pos` 및 `.../joint2/cmd_pos`이고 ROS에서는 브리지로 짧게 매핑되어 있다. Gazebo 쪽 joint state는 `gz.msgs.Model`이며 ROS의 `sensor_msgs/msg/JointState`로 바뀐다.

## 3. 관절별 입력
```bash
ros2 topic pub --once /joint1/cmd_pos std_msgs/msg/Float64 '{data: 0.5}'
ros2 topic pub --once /joint2/cmd_pos std_msgs/msg/Float64 '{data: -0.5}'
ros2 topic echo /joint_states
```
**예상 변화**: joint1=+0.5rad, joint2=-0.5rad 쪽으로 위치 변동. 응답 시간·정확도는 실제 상태 토픽으로 관측해야 한다. 목표값에 정확히 도달한다고 미리 단정할 수 없다. 한 번씩 0rad 명령으로 복귀 후 각도 변화와 RTF를 비교한다.

## 4. 제어 원리 비교
- P: 위치 오차에 비례하는 구동 출력.
- I: 지속 오차 누적 보상(포화·windup에 주의).
- D: 급변 억제. 상태 피드백·디스크리트 주기·하중에 따라 튜닝 필요.
- `update_rate=50`은 **JointState 출력 주기**이지 시뮬레이션 적분 주기(1ms)가 아니다.

실험용 복사본에서 P 값을 줄이거나 D 값을 바꿔 joint 응답 그래프/로그를 비교하되, 물리적으로 안정적인 gain이라고 인증하지 않는다. ROS에서 `use_sim_time`을 true로 유지한다.

## 5. 성공 판정 / 트러블슈팅
- [ ] 플러그인 로딩 에러 0, joint_states에 joint1·joint2 모두 존재
- [ ] 두 명령 토픽 ROS→Gazebo 연결됨
- [ ] 명령 변화 후 실제 위치 변화 확인 및 로그 저장
- [ ] 시간 변화·베이스 위치 변화·CPU/RTF 확인
- [ ] 명령값 제약 ±1.57rad(joint2), ±3.14rad(joint1) 준수

`/joint_states`가 없다면 world 이름·Gazebo 플러그인·bridge YAML을 순차 확인. 관절이 움직이지 않으면 시뮬레이션 일시정지, Gazebo cmd_pos 토픽 및 컨트롤러 플러그인 로딩을 확인. [리뷰](SECTION_3_8_REPORT_KO.md).
