# LAB 3.9 — 키보드로 2축 로봇 팔 조작하기

## 목표
키 입력 → 각도 증감·클램프 → ROS Float64 메시지 → 브리지 → Gazebo PID 제어 → 관절 상태 확인. **명령을 보낸 것과 실제 각도가 바뀐 것은 다르다.**

## 1. 준비 (선행 3.3/3.6/3.7/3.8 PR의 수정이 모두 반영된 상태)
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 pkg executables my_robot_description
```
예상: `simple_arm_teleop`과 `joint_control_cli` 노드가 보인다. `setup.py` 등록은 소스에 이미 존재하므로 재작성하지 않는다.

## 2. 터미널 A — 시뮬레이터
```bash
ros2 launch my_robot_description spawn_robot.launch.py
```
Gazebo 창과 스폰/브리지 로딩 로그를 확인한다. WSLg가 불안정하면 3.4절의 GUI-서버 분리 진단을 먼저 수행한다.

## 3. 터미널 B — 사용자 입력
```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch03/ros2_ws/install/setup.bash
ros2 run my_robot_description simple_arm_teleop
```
**실제 키 매핑**: W/S = joint1 ±0.05rad, A/D = joint2 ±0.05rad, Q = 정상 종료. 대소문자 모두 허용. 별도 Enter 없이 입력한다. 관절각 소프트웨어 제약은 각각 ±1.57rad이다. 키 이벤트 이외의 idle 구간에는 동일 명령을 재전송하지 않는다.

## 4. 터미널 C — 계측
```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch03/ros2_ws/install/setup.bash
ros2 topic echo /joint_states
ros2 topic info /joint1/cmd_pos -v
ros2 topic info /joint2/cmd_pos -v
```
W를 5회 누르면 명령 목표가 +0.25rad로 증가한다. 실제 `/joint_states` 측정값이 이를 추종하는지는 PID/시뮬레이션 상태에 의존한다. A 4회는 joint2 +0.20rad 목표다. 여러 번 눌러도 한계 ±1.57rad를 넘지 않는지 확인한다.

## 5. 실패 시 진단
- 입력이 안 된다: 터미널 B 포커스·인터랙티브 TTY 확인. GUI 노드에서 teleop을 백그라운드로 띄우지 말 것
- 명령 토픽은 발행되지만 팔이 고정: Gazebo `gz topic -l`의 `/model/my_robot/joint1/cmd_pos` / `joint2/cmd_pos` 확인
- `/joint_states` 없음: 3.8 Gazebo publisher와 3.6 브리지부터 확인
- 모델 기울어짐: 베이스의 물리적 고정은 본 2-DOF URDF만으로 보장되지 않음
- 종료 후 셸 입력이 이상: `stty sane`으로 복구 후 재현 로그 확보

## 합격·Evidence
`stty -a` 정상 복귀, 키 입력→명령 목표→관절각 변화의 연속 로그, 정지시 안전 여부, 한계 포화, Ctrl+C/q 종료 화면을 제출. 실습 자체는 실제 로봇 하드웨어 안전성을 입증하지 않는다. [리뷰](SECTION_3_9_REPORT_KO.md).
